#!/usr/bin/env python3
"""
Improved startup script for CyberScore with better error handling and configuration
"""

import subprocess
import sys
import time
import os
import signal
import psutil
from pathlib import Path
from utils.logger import get_logger
from config import settings

logger = get_logger(__name__)


class ProcessManager:
    """Manage backend and frontend processes"""

    def __init__(self):
        self.backend_process = None
        self.frontend_process = None
        self.running = False

    def start_backend(self):
        """Start the FastAPI backend"""
        try:
            logger.info("Starting FastAPI backend...")
            self.backend_process = subprocess.Popen(
                [
                    sys.executable,
                    "-m",
                    "uvicorn",
                    "backend.api:app",
                    "--host",
                    settings.api_host,
                    "--port",
                    str(settings.api_port),
                    "--reload" if settings.reload else "--no-reload",
                ]
            )
            logger.info(f"Backend started with PID: {self.backend_process.pid}")
            return True
        except Exception as e:
            logger.error(f"Failed to start backend: {e}")
            return False

    def start_frontend(self):
        """Start the Streamlit frontend"""
        try:
            logger.info("Starting Streamlit frontend...")
            self.frontend_process = subprocess.Popen(
                [
                    sys.executable,
                    "-m",
                    "streamlit",
                    "run",
                    "app_with_auth.py",
                    "--server.port",
                    str(settings.frontend_port),
                    "--server.address",
                    settings.frontend_host,
                ]
            )
            logger.info(f"Frontend started with PID: {self.frontend_process.pid}")
            return True
        except Exception as e:
            logger.error(f"Failed to start frontend: {e}")
            return False

    def check_processes(self):
        """Check if processes are still running"""
        backend_running = self.backend_process and self.backend_process.poll() is None
        frontend_running = (
            self.frontend_process and self.frontend_process.poll() is None
        )
        return backend_running, frontend_running

    def stop_processes(self):
        """Stop all processes"""
        logger.info("Stopping processes...")

        if self.backend_process:
            try:
                self.backend_process.terminate()
                self.backend_process.wait(timeout=5)
                logger.info("Backend stopped")
            except subprocess.TimeoutExpired:
                self.backend_process.kill()
                logger.warning("Backend force killed")
            except Exception as e:
                logger.error(f"Error stopping backend: {e}")

        if self.frontend_process:
            try:
                self.frontend_process.terminate()
                self.frontend_process.wait(timeout=5)
                logger.info("Frontend stopped")
            except subprocess.TimeoutExpired:
                self.frontend_process.kill()
                logger.warning("Frontend force killed")
            except Exception as e:
                logger.error(f"Error stopping frontend: {e}")

    def cleanup_zombie_processes(self):
        """Clean up any zombie processes"""
        try:
            for proc in psutil.process_iter(["pid", "name", "cmdline"]):
                try:
                    cmdline = proc.info["cmdline"]
                    if cmdline and any(
                        "uvicorn" in arg or "streamlit" in arg for arg in cmdline
                    ):
                        if "cyberscore" in " ".join(cmdline).lower():
                            logger.info(
                                f"Cleaning up zombie process: {proc.info['pid']}"
                            )
                            proc.terminate()
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    pass
        except Exception as e:
            logger.warning(f"Error cleaning up zombie processes: {e}")


def signal_handler(signum, frame):
    """Handle shutdown signals"""
    logger.info(f"Received signal {signum}, shutting down...")
    process_manager.stop_processes()
    sys.exit(0)


def main():
    """Main startup function"""
    print("🛡️ Starting CyberScore with Enhanced Features")
    print("=" * 60)

    # Setup signal handlers
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    # Change to project directory
    project_dir = Path(__file__).parent
    os.chdir(project_dir)

    # Initialize process manager
    global process_manager
    process_manager = ProcessManager()

    try:
        # Clean up any existing processes
        process_manager.cleanup_zombie_processes()

        # Start backend
        if not process_manager.start_backend():
            logger.error("Failed to start backend")
            sys.exit(1)

        # Wait for backend to start
        logger.info("Waiting for backend to initialize...")
        time.sleep(3)

        # Start frontend
        if not process_manager.start_frontend():
            logger.error("Failed to start frontend")
            process_manager.stop_processes()
            sys.exit(1)

        # Display startup info
        print("\nBoth servers started successfully!")
        print(f"\nFrontend: http://{settings.frontend_host}:{settings.frontend_port}")
        print(f"Backend API: http://{settings.api_host}:{settings.api_port}")
        print(f"API Docs: http://{settings.api_host}:{settings.api_port}/docs")
        print(f"\nLogs: logs/{settings.log_file}")
        print("\nPress Ctrl+C to stop both servers")

        # Monitor processes
        while True:
            backend_running, frontend_running = process_manager.check_processes()

            if not backend_running:
                logger.error("Backend process died, restarting...")
                if not process_manager.start_backend():
                    logger.error("Failed to restart backend")
                    break

            if not frontend_running:
                logger.error("Frontend process died, restarting...")
                if not process_manager.start_frontend():
                    logger.error("Failed to restart frontend")
                    break

            time.sleep(5)  # Check every 5 seconds

    except KeyboardInterrupt:
        logger.info("Received keyboard interrupt")
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
    finally:
        process_manager.stop_processes()
        logger.info("Shutdown complete")


if __name__ == "__main__":
    main()
