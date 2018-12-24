import pkg_resources


_res_manager = pkg_resources.ResourceManager()
_res_provider = pkg_resources.get_provider(__name__)

def get_resource_string(path):
    return _res_provider.get_resource_string(_res_manager, path).decode('utf-8')
