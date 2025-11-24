def calculate_edges(works_data):
    """
    Рассчитывает связи между работами в формате (begin, end)
    
    Args:
        works_data: список работ в формате (name, dependencies, t_pes, t_ver, t_opt, cost_reduction)
    
    Returns:
        list: список кортежей (begin_node, end_node) для каждого ребра
    """
    edges = []
    
    # Создаем маппинг имен работ к номерам узлов
    work_to_node = {}
    for i, (name, _, _, _, _, _) in enumerate(works_data):
        work_to_node[name] = i
    
    # Для каждой работы создаем связи с ее зависимостями
    for work_name, dependencies, _, _, _, _ in works_data:
        work_node = work_to_node[work_name]
        
        for dep in dependencies:
            if dep != '-':  # Пропускаем работы без зависимостей
                dep_node = work_to_node[dep]
                edges.append((dep_node, work_node))
    
    return edges