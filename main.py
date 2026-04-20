import os
import sys

from web.app import app, init_application

if __name__ == "__main__":
    import threading
    # Run initialization in a background thread to allow the server to start immediately
    init_thread = threading.Thread(target=init_application, daemon=True)
    init_thread.start()
    init_thread.join()  # Wait for initialization to complete before starting server
    
    # Start the web server immediately
    app.run(host="0.0.0.0", port=5000, debug=True, use_reloader=False)