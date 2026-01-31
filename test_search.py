import requests

# Test 1: Empty search (should return all 500 jobs)
r = requests.get('http://localhost:5000/api/search', params={
    'q': '',
    'city': 'All Locations',
    'offset': 0,
    'limit': 500,
    'exp': 'intern,junior,senior,lead',
    'type': 'full,part,remote,contract',
    'min_salary': 0
})
d = r.json()
print(f'Test 1 - Empty search: Total: {d["total"]}, Jobs returned: {len(d["jobs"])}')

# Test 2: Search for "python"
r2 = requests.get('http://localhost:5000/api/search', params={
    'q': 'python',
    'city': 'All Locations',
    'offset': 0,
    'limit': 500,
    'exp': 'intern,junior,senior,lead',
    'type': 'full,part,remote,contract',
    'min_salary': 0
})
d2 = r2.json()
print(f'Test 2 - Search "python": Total: {d2["total"]}, Jobs returned: {len(d2["jobs"])}')

# Test 3: Search for "data"
r3 = requests.get('http://localhost:5000/api/search', params={
    'q': 'data',
    'city': 'All Locations',
    'offset': 0,
    'limit': 500,
    'exp': 'intern,junior,senior,lead',
    'type': 'full,part,remote,contract',
    'min_salary': 0
})
d3 = r3.json()
print(f'Test 3 - Search "data": Total: {d3["total"]}, Jobs returned: {len(d3["jobs"])}')
