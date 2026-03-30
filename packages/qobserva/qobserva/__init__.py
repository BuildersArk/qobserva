"""QObserva - Unified quantum observability package."""

__version__ = "0.1.3"

# Re-export agent functionality
# The agent package provides 'qobserva' module, but we also use 'qobserva'
# Solution: Import from agent's source directly using importlib

try:
    import sys
    import importlib
    from pathlib import Path
    
    # Find the agent package's source
    current_file = Path(__file__)
    packages_dir = current_file.parent.parent.parent
    agent_qobserva_dir = packages_dir / "qobserva_agent" / "qobserva"
    
    if not agent_qobserva_dir.exists():
        raise ImportError(f"Agent directory not found at {agent_qobserva_dir}")
    
    # Method 1: Try importing from installed agent package
    # The agent package installs as 'qobserva' module, but we need to get it
    # before our module loads. Since we're already loaded, we need a workaround.
    
    # Method 2: Load agent's __init__.py directly and execute in isolated namespace
    agent_init = agent_qobserva_dir / "__init__.py"
    if agent_init.exists():
        # Read and execute the agent's __init__.py in a way that allows imports
        import importlib.util
        
        # Use importlib.machinery for loading
        from importlib import machinery
        
        # We need to set up the module's __package__ and __path__ for relative imports
        # But this is complex. Let's try a different approach:
        # Import the agent's submodules directly by adding parent to path
        
        agent_parent = agent_qobserva_dir.parent
        saved_path = sys.path[:]
        
        # Remove any qobserva modules temporarily
        saved_modules = {k: v for k, v in sys.modules.items() if k.startswith('qobserva')}
        for key in list(saved_modules.keys()):
            if key != 'qobserva.qobserva':  # Keep our own module
                del sys.modules[key]
        
        sys.path.insert(0, str(agent_parent))
        
        try:
            # Import agent's qobserva as a different name to avoid conflict
            spec = importlib.util.spec_from_file_location(
                "agent_qobserva",
                agent_init,
                submodule_search_locations=[str(agent_qobserva_dir)]
            )
            agent_qobserva = importlib.util.module_from_spec(spec)
            agent_qobserva.__package__ = "qobserva"
            agent_qobserva.__path__ = [str(agent_qobserva_dir)]
            spec.loader.exec_module(agent_qobserva)
            
            observe_run = agent_qobserva.observe_run
            QObservaClient = agent_qobserva.QObservaClient
            report_run = agent_qobserva.report_run
        finally:
            sys.path[:] = saved_path
            # Restore saved modules except our own
            for key, value in saved_modules.items():
                if key != 'qobserva' and not key.startswith('qobserva.qobserva'):
                    sys.modules[key] = value
    else:
        raise ImportError(f"Agent __init__.py not found at {agent_init}")
    
    __all__ = ['observe_run', 'QObservaClient', 'report_run', '__version__']
except (ImportError, AttributeError, Exception) as import_error:
    # Store the error for use in the fallback functions
    _import_error = import_error
    
    # If agent is not installed or import fails, provide helpful error
    def observe_run(*args, **kwargs):
        raise ImportError(
            f"qobserva-agent is not installed or cannot be imported.\n"
            f"Install it with: pip install -e packages/qobserva_agent\n"
            f"Original error: {_import_error}"
        )
    
    class QObservaClient:
        pass
    
    def report_run(*args, **kwargs):
        raise ImportError(
            f"qobserva-agent is not installed or cannot be imported.\n"
            f"Install it with: pip install -e packages/qobserva_agent\n"
            f"Original error: {_import_error}"
        )
    
    __all__ = ['observe_run', 'QObservaClient', 'report_run', '__version__']
