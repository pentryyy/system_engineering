from collections import defaultdict
import networkx as nx

def calculate_positions(graph, dummy_tasks):
    # Определяем слои для каждого узла
    layers = {}
    for node in nx.topological_sort(graph):
        if graph.in_degree(node) == 0:
            layers[node] = 0
        else:
            layers[node] = max(layers[pred] for pred in graph.predecessors(node)) + 1
    
    # Группируем узлы по слоям
    layer_groups = defaultdict(list)
    for node, layer in layers.items():
        layer_groups[layer].append(node)
    
    # Рассчитываем координаты
    pos = {}
    for layer, nodes in layer_groups.items():
        nodes_sorted = sorted(nodes)
        num_nodes = len(nodes_sorted)
        for idx, node in enumerate(nodes_sorted):
            y = idx / max(1, num_nodes - 1)  # Нормализация Y от 0 до 1
            pos[node] = (layer * 2, y)       # Умножаем X для увеличения расстояния
    
    
    count_of_dummies = len(dummy_tasks)
    if count_of_dummies != 0:

        level_threshold = 0.5

        # Смещаем все элементы на половину от графика
        for node in pos:
            x, y = pos[node]

            if y <= level_threshold:  
                pos[node] = (x, y + level_threshold)

        offset = level_threshold / count_of_dummies
        
        local_offset_low  = 0
        local_offset_high = 0

        for dummy in dummy_tasks:
            
            dep_end = dummy[1]

            dep_end_y = pos[dep_end][1] # Значение по оси y для конечной точки
            if dep_end_y <= 0.5: 

                # Элемент снизу
                local_offset_low += offset
            
                pos[dep_end] = (
                    pos[dep_end][0], 
                    dep_end_y - local_offset_low
                )
            else:

                # Элемент сверху
                local_offset_high += offset

                pos[dep_end] = (
                    pos[dep_end][0], 
                    dep_end_y - local_offset_high
                )

    return pos

def create_network_with_dummies(works_data):
    """
    Создает сетевой график с фиктивными работами
    
    Args:
        works_data: список работ в формате (name, dependencies, t_pes, t_ver, t_opt, cost_reduction)
    
    Returns:
        tuple: (graph, dummy_tasks, work_to_node)
    """
    G = nx.DiGraph()
    dummy_tasks = []
    
    # Создаем узлы (события) - по одному на каждую работу
    num_nodes = len(works_data)
    for i in range(num_nodes):
        G.add_node(i)
    
    # Создаем маппинг имен работ к номерам узлов
    work_to_node = {}
    for i, (name, _, _, _, _, _) in enumerate(works_data):
        work_to_node[name] = i
    
    # Словарь для хранения информации о работах
    task_info = {}
    for name, dependencies, t_pes, t_ver, t_opt, cost_reduction in works_data:
        task_info[name] = {
            'dependencies': dependencies,
            't_pes': t_pes,
            't_ver': t_ver,
            't_opt': t_opt,
            'cost_reduction': cost_reduction
        }
    
    # Сначала добавляем все реальные работы
    for name, dependencies, t_pes, t_ver, t_opt, cost_reduction in works_data:
        work_node = work_to_node[name]
        
        # Для работ без зависимостей - начинаем с узла 0
        if dependencies == ['-']:
            start_node = 0
            G.add_edge(
                start_node, work_node,
                task=name,
                duration=(t_pes + 4 * t_ver + t_opt) / 6,  # t_oj для трехпараметрической модели
                real=True,
                t_pes=t_pes,
                t_ver=t_ver, 
                t_opt=t_opt,
                cost_reduction=cost_reduction
            )
        else:
            # Для работ с зависимостями - создаем связи от зависимых работ
            for dep in dependencies:
                if dep != '-':
                    dep_node = work_to_node[dep]
                    G.add_edge(
                        dep_node, work_node,
                        task=name,
                        duration=(t_pes + 4 * t_ver + t_opt) / 6,
                        real=True,
                        t_pes=t_pes,
                        t_ver=t_ver,
                        t_opt=t_opt,
                        cost_reduction=cost_reduction
                    )
    
    # Теперь добавляем фиктивные работы там, где это необходимо
    for name, dependencies, _, _, _, _ in works_data:
        if dependencies != ['-']:
            work_node = work_to_node[name]
            
            # Для работ с несколькими зависимостями проверяем необходимость фиктивных работ
            if len(dependencies) > 1:
                # Получаем все конечные узлы зависимостей
                dep_end_nodes = [work_to_node[dep] for dep in dependencies if dep != '-']
                
                # Проверяем пары зависимостей на необходимость фиктивных связей
                for i in range(len(dep_end_nodes)):
                    for j in range(i + 1, len(dep_end_nodes)):
                        dep1 = dep_end_nodes[i]
                        dep2 = dep_end_nodes[j]
                        
                        # Проверяем, связаны ли уже эти зависимости
                        if not G.has_edge(dep1, dep2) and not G.has_edge(dep2, dep1):
                            # Добавляем фиктивную работу от более ранней к более поздней зависимости
                            # Определяем какая зависимость должна быть раньше на основе топологии
                            if dep1 < dep2:  # Простая эвристика - можно улучшить
                                source, target = dep1, dep2
                            else:
                                source, target = dep2, dep1
                            
                            # Проверяем, нет ли уже связи
                            if not G.has_edge(source, target):
                                dummy_name = f"dummy_{source}_{target}"
                                dummy_tasks.append((source, target))
                                
                                G.add_edge(
                                    source, target,
                                    task=dummy_name,
                                    duration=0,
                                    real=False
                                )
    
    # Дополнительная проверка: фиктивные работы для правильной последовательности
    # Особенно для работ с общими зависимостями
    for name, dependencies, _, _, _, _ in works_data:
        work_node = work_to_node[name]
        
        if dependencies != ['-'] and len(dependencies) > 1:
            # Для работ типа b9, b10, b11 которые имеют несколько зависимостей
            dep_nodes = [work_to_node[dep] for dep in dependencies if dep != '-']
            
            # Упорядочиваем зависимости по номерам узлов
            dep_nodes_sorted = sorted(dep_nodes)
            
            # Создаем цепочку фиктивных работ между зависимостями
            for i in range(len(dep_nodes_sorted) - 1):
                source = dep_nodes_sorted[i]
                target = dep_nodes_sorted[i + 1]
                
                if not G.has_edge(source, target):
                    dummy_name = f"dummy_chain_{source}_{target}"
                    dummy_tasks.append((source, target))
                    
                    G.add_edge(
                        source, target,
                        task=dummy_name,
                        duration=0,
                        real=False
                    )
    
    return G, dummy_tasks, work_to_node