#!/usr/bin/env python3
"""
Simple launcher for the Gradescope Downloader UI
"""

import sys
import os
import asyncio

def main():
    """Launch the Gradescope downloader with UI"""
    try:
        # Add current directory to path to import our modules
        sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
        
        from gradescope_ui import main as ui_main
        asyncio.run(ui_main())
        
    except ImportError as e:
        print(f"❌ Import error: {e}")
        print("Make sure you have installed the required dependencies:")
        print("pip install -r requirements.txt")
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    main()
