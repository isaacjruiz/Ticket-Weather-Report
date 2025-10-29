import sys
import importlib.util

# Load the module directly
spec = importlib.util.spec_from_file_location("test_integration", "tests/test_integration.py")
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)

# Check what's in the module
print("Module attributes:")
for attr in dir(module):
    if not attr.startswith('_'):
        print(f"  {attr}: {type(getattr(module, attr))}")

# Check if TestWeatherServiceIntegration exists
if hasattr(module, 'TestWeatherServiceIntegration'):
    cls = getattr(module, 'TestWeatherServiceIntegration')
    print(f"\nTestWeatherServiceIntegration methods:")
    for method in dir(cls):
        if method.startswith('test_'):
            print(f"  {method}")
else:
    print("\nTestWeatherServiceIntegration not found!")