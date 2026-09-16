"""Pure numeric extraction/comparison migrated from tutorial_tasks; no runtime policy."""


def list_values(value):
    def group(index):
        if value[index] != '(':
            raise ValueError('Expected literal list')
        index += 1
        result = []
        while index < len(value) and value[index] != ')':
            if value[index] == '(':
                item, index = group(index)
            else:
                item = value[index]
                index += 1
            result.append(item)
        if index == len(value):
            raise ValueError('Incomplete literal list')
        return result, index+1
    result, end = group(0)
    if end != len(value):
        raise ValueError('Extra tokens after literal list')
    return result
