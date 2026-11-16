def binary_search(sorted_list, target):
    low, high = 0, len(sorted_list) - 1
    while low < high:
        mid = (low + high) // 2
        if sorted_list[mid] > target:
            low = mid + 1
        else:
            high = mid
    if sorted_list and sorted_list[low] == target:
        return low
    return -1
