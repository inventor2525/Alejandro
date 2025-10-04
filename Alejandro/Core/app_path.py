import os
def app_path(relative_folder_path:str, file_name:str=None) -> str:
	app_root = os.path.expanduser("~/Documents/Alejandro/")
	
	if relative_folder_path.startswith('/'):
		relative_folder_path = relative_folder_path[1:]
	if relative_folder_path.endswith('/'):
		relative_folder_path = relative_folder_path[0:-2]
	
	final_path = app_root
	if relative_folder_path:
		final_path = os.path.join(final_path, relative_folder_path)
	
	os.makedirs(final_path, exist_ok=True)
	
	if file_name:
		final_path = os.path.join(final_path, file_name)
	return final_path