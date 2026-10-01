import os

def setup_esm_production_structure():
    # Root and main folders
    base_dir = "esm_project"
    apps_dir = os.path.join(base_dir, "apps")
    
    # All 10 Production Modules
    modules = [
        "iam", "studio", "engine", "infrastructure", 
        "scheduler", "monitoring", "vault", "compliance", "maintenance"
    ]
    
    # Standard Django App files + Production specific files
    app_files = [
        "__init__.py", "models.py", "views.py", 
        "serializers.py", "urls.py", "tasks.py", "signals.py"
    ]
    
    try:
        # Create core project directories
        os.makedirs(os.path.join(base_dir, "esm_core"), exist_ok=True)
        os.makedirs(apps_dir, exist_ok=True)
        
        # 1. Create Core Config Files
        core_path = os.path.join(base_dir, "esm_core")
        for f in ["__init__.py", "settings.py", "urls.py", "celery.py", "wsgi.py", "asgi.py"]:
            open(os.path.join(core_path, f), 'a').close()
            
        # 2. Create Module Folders and Files
        for mod in modules:
            mod_path = os.path.join(apps_dir, mod)
            os.makedirs(mod_path, exist_ok=True)
            for f in app_files:
                open(os.path.join(mod_path, f), 'a').close()
        
        # 3. Create Root Project Files
        root_files = ["manage.py", "requirements.txt", "docker-compose.yml", ".env", ".gitignore"]
        for f in root_files:
            open(os.path.join(base_dir, f), 'a').close()
            
        print(f"✅ ESM Production Structure created successfully at: /{base_dir}")
        print(f"🚀 Total Modules Initialized: {len(modules)}")
        
    except Exception as e:
        print(f"❌ Error creating structure: {e}")

if __name__ == "__main__":
    setup_esm_production_structure()
