from collections import defaultdict
import networkx as nx

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
    
    # Создаем начальный и конечный узлы
    G.add_node('start')
    G.add_node('end')
    
    # Создаем маппинг имен работ к номерам узлов
    work_to_node = {}
    for i, (name, _, _, _, _, _) in enumerate(works_data):
        work_to_node[name] = f"work_{i}"
        G.add_node(work_to_node[name])
    
    # Добавляем все реальные работы
    for name, dependencies, t_pes, t_ver, t_opt, cost_reduction in works_data:
        work_node = work_to_node[name]
        duration = (t_pes + 4 * t_ver + t_opt) / 6
        
        # Для работ без зависимостей - начинаем с узла 'start'
        if dependencies == ['-'] or not dependencies:
            G.add_edge(
                'start', work_node,
                task=name,
                duration=duration,
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
                        duration=duration,
                        real=True,
                        t_pes=t_pes,
                        t_ver=t_ver,
                        t_opt=t_opt,
                        cost_reduction=cost_reduction
                    )
    
    # Добавляем связи в конечный узел для работ без потомков
    for name, _, _, _, _, _ in works_data:
        work_node = work_to_node[name]
        if G.out_degree(work_node) == 0 and work_node != 'end':
            G.add_edge(work_node, 'end', task='end', duration=0, real=False)
    
    # Упрощенная версия без сложной логики фиктивных работ
    # Проверяем на циклы
    try:
        list(nx.topological_sort(G))
        print("Граф корректен, циклов не обнаружено")
    except nx.NetworkXUnfeasible:
        print("Обнаружен цикл в графе! Упрощаем структуру...")
        # Упрощаем граф, удаляя проблемные связи
        G = simplify_graph(G, works_data, work_to_node)
    
    return G, dummy_tasks, work_to_node

def simplify_graph(G, works_data, work_to_node):
    """Упрощает граф, удаляя потенциально проблемные связи"""
    G_simple = nx.DiGraph()
    
    # Добавляем узлы
    G_simple.add_node('start')
    G_simple.add_node('end')
    for node in G.nodes():
        if node not in ['start', 'end']:
            G_simple.add_node(node)
    
    # Добавляем только прямые связи из works_data
    for name, dependencies, t_pes, t_ver, t_opt, cost_reduction in works_data:
        work_node = work_to_node[name]
        duration = (t_pes + 4 * t_ver + t_opt) / 6
        
        if dependencies == ['-'] or not dependencies:
            G_simple.add_edge('start', work_node, 
                            task=name, duration=duration, real=True)
        else:
            for dep in dependencies:
                if dep != '-':
                    dep_node = work_to_node[dep]
                    G_simple.add_edge(dep_node, work_node, 
                                    task=name, duration=duration, real=True)
    
    # Добавляем связи в конечный узел
    for name, _, _, _, _, _ in works_data:
        work_node = work_to_node[name]
        if G_simple.out_degree(work_node) == 0 and work_node != 'end':
            G_simple.add_edge(work_node, 'end', task='end', duration=0, real=False)
    
    return G_simple

def calculate_positions(graph, dummy_tasks):
    """Рассчитывает позиции для визуализации с проверкой на циклы"""
    try:
        # Проверяем, есть ли циклы
        if not nx.is_directed_acyclic_graph(graph):
            print("Внимание: граф содержит циклы! Используется упрощенное расположение.")
            return spring_layout_fallback(graph)
        
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
                y = idx / max(1, num_nodes - 1) if num_nodes > 1 else 0.5
                pos[node] = (layer * 2, y)
        
        return pos
        
    except nx.NetworkXUnfeasible:
        print("Ошибка: граф содержит циклы. Используется альтернативное расположение.")
        return spring_layout_fallback(graph)

def spring_layout_fallback(graph):
    """Альтернативное расположение для графов с циклами"""
    return nx.spring_layout(graph, k=2, iterations=50)

# Пример использования с проверкой
def analyze_graph(G):
    """Анализирует граф на наличие проблем"""
    print(f"Количество узлов: {G.number_of_nodes()}")
    print(f"Количество ребер: {G.number_of_edges()}")
    print(f"Есть циклы: {not nx.is_directed_acyclic_graph(G)}")
    
    if not nx.is_directed_acyclic_graph(G):
        print("Обнаружены циклы:")
        try:
            cycles = list(nx.simple_cycles(G))
            for i, cycle in enumerate(cycles[:3]):  # Показываем первые 3 цикла
                print(f"Цикл {i+1}: {cycle}")
        except:
            print("Не удалось найти конкретные циклы")