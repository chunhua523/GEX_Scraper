import customtkinter as ctk
import asyncio
import sys
from gui import LietaApp

# Set appearance mode and color theme
ctk.set_appearance_mode("Dark")  # Modes: "System" (standard), "Dark", "Light"
ctk.set_default_color_theme("blue")  # Themes: "blue" (standard), "green", "dark-blue"

def main():
    app = LietaApp()
    app.mainloop()

if __name__ == "__main__":
    main()
