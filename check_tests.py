import tests.test_integration
import inspect

print('Classes found:')
for name, obj in inspect.getmembers(tests.test_integration):
    if inspect.isclass(obj):
        print(f'  {name}')
        for method_name, method in inspect.getmembers(obj):
            if method_name.startswith('test_'):
                print(f'    {method_name}')