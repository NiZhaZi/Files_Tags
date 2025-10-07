#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Tag-based file lister & opener (Tkinter UI).

- Loads a JSON database of files and their categorized tags.
- Lets you filter by tags (AND / OR) and by filename substring.
- Lists matching files and allows opening them with the system default app.
- English-only UI strings, suitable for packaging as a single executable.

Author: You
"""

from __future__ import annotations

import os
import sys
import subprocess
import traceback
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from typing import List, Tuple, Optional

from tag_db import TagDB, TagKey


APP_TITLE = "Tag File Browser"
ABOUT_TEXT = (
    "Tag File Browser\n"
    "Filter files by categorized tags and open them.\n\n"
    "JSON schema:\n"
    "{ 'files': [ {'path': '/abs/path', 'tags': [{'category': '...', 'name': '...'}]} ] }"
)


def open_with_system(path: str) -> None:
    """Open a file or directory using the OS default handler."""
    try:
        if sys.platform.startswith("win"):
            os.startfile(path)  # type: ignore[attr-defined]
        elif sys.platform == "darwin":
            subprocess.run(["open", path], check=False)
        else:
            subprocess.run(["xdg-open", path], check=False)
    except Exception as e:
        messagebox.showerror("Open Failed", f"Could not open:\n{path}\n\n{e}")


class TagFileBrowser(tk.Tk):
    def __init__(self, db_path: Optional[str] = None) -> None:
        super().__init__()
        self.title(APP_TITLE)
        self.minsize(900, 560)

        self.db = TagDB()
        self.selected_filters: List[TagKey] = []

        self._build_menu()
        self._build_widgets()
        self._configure_layout()

        if db_path:
            self._load_db_safely(db_path)

    # ---------- UI construction ----------
    def _build_menu(self) -> None:
        menubar = tk.Menu(self)

        file_menu = tk.Menu(menubar, tearoff=0)
        file_menu.add_command(label="Open Tag DB…", command=self.on_open_db, accelerator="Ctrl+O")
        file_menu.add_command(label="Reload DB", command=self.on_reload_db, accelerator="Ctrl+R")
        file_menu.add_separator()
        file_menu.add_command(label="Quit", command=self.on_quit, accelerator="Ctrl+Q")
        menubar.add_cascade(label="File", menu=file_menu)

        help_menu = tk.Menu(menubar, tearoff=0)
        help_menu.add_command(label="About", command=lambda: messagebox.showinfo("About", ABOUT_TEXT))
        menubar.add_cascade(label="Help", menu=help_menu)

        self.config(menu=menubar)

        # Shortcuts
        self.bind_all("<Control-o>", lambda e: self.on_open_db())
        self.bind_all("<Control-r>", lambda e: self.on_reload_db())
        self.bind_all("<Control-q>", lambda e: self.on_quit())

    def _build_widgets(self) -> None:
        # Top: DB path and actions
        top = ttk.Frame(self)
        top.pack(side=tk.TOP, fill=tk.X, padx=8, pady=6)

        ttk.Label(top, text="DB:").pack(side=tk.LEFT)
        self.db_path_var = tk.StringVar(value="(no database loaded)")
        self.db_path_entry = ttk.Entry(top, textvariable=self.db_path_var, state="readonly")
        self.db_path_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=6)
        ttk.Button(top, text="Open…", command=self.on_open_db).pack(side=tk.LEFT, padx=4)
        ttk.Button(top, text="Reload", command=self.on_reload_db).pack(side=tk.LEFT, padx=4)

        # Main: split left (filters) / right (files)
        main = ttk.Panedwindow(self, orient=tk.HORIZONTAL)
        main.pack(side=tk.TOP, fill=tk.BOTH, expand=True, padx=8, pady=(0, 8))

        # Left panel: tag selector and active filters
        left = ttk.Frame(main)
        main.add(left, weight=1)

        # Category -> Tag list
        selector = ttk.LabelFrame(left, text="Select Tags")
        selector.pack(side=tk.TOP, fill=tk.BOTH, expand=False, padx=4, pady=4)

        row = ttk.Frame(selector)
        row.pack(side=tk.TOP, fill=tk.X, padx=6, pady=(6, 0))
        ttk.Label(row, text="Category:").pack(side=tk.LEFT)
        self.category_cmb = ttk.Combobox(row, state="readonly", values=[])
        self.category_cmb.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=6)
        self.category_cmb.bind("<<ComboboxSelected>>", lambda e: self._refresh_tag_list())

        # Tag Listbox for selected category
        self.tag_list = tk.Listbox(selector, selectmode=tk.EXTENDED, height=10)
        self.tag_list.pack(side=tk.TOP, fill=tk.BOTH, expand=True, padx=6, pady=(6, 6))

        add_row = ttk.Frame(selector)
        add_row.pack(side=tk.TOP, fill=tk.X, padx=6, pady=(0, 8))
        ttk.Button(add_row, text="Add Selected Tags", command=self.on_add_selected_tags).pack(side=tk.LEFT)

        # Active filters
        active = ttk.LabelFrame(left, text="Active Tag Filters")
        active.pack(side=tk.TOP, fill=tk.BOTH, expand=True, padx=4, pady=4)

        self.filter_tree = ttk.Treeview(active, columns=("category", "tag"), show="headings", selectmode="extended")
        self.filter_tree.heading("category", text="Category")
        self.filter_tree.heading("tag", text="Tag")
        self.filter_tree.column("category", width=120, anchor=tk.W)
        self.filter_tree.column("tag", width=160, anchor=tk.W)
        self.filter_tree.pack(side=tk.TOP, fill=tk.BOTH, expand=True, padx=6, pady=6)

        filter_btns = ttk.Frame(active)
        filter_btns.pack(side=tk.TOP, fill=tk.X, padx=6, pady=(0, 8))
        ttk.Button(filter_btns, text="Remove Selected", command=self.on_remove_selected_filters).pack(side=tk.LEFT)
        ttk.Button(filter_btns, text="Clear All", command=self.on_clear_filters).pack(side=tk.LEFT, padx=6)

        # Mode + name filter
        options = ttk.LabelFrame(left, text="Filter Options")
        options.pack(side=tk.TOP, fill=tk.X, expand=False, padx=4, pady=(0, 4))

        self.mode_var = tk.StringVar(value="AND")
        ttk.Radiobutton(options, text="Match ALL (AND)", variable=self.mode_var, value="AND", command=self.refresh_results).pack(side=tk.LEFT, padx=6, pady=6)
        ttk.Radiobutton(options, text="Match ANY (OR)", variable=self.mode_var, value="OR", command=self.refresh_results).pack(side=tk.LEFT, padx=6, pady=6)

        ttk.Label(options, text="Filename contains:").pack(side=tk.LEFT, padx=(12, 4))
        self.name_filter_var = tk.StringVar()
        name_entry = ttk.Entry(options, textvariable=self.name_filter_var, width=20)
        name_entry.pack(side=tk.LEFT, padx=(0, 6))
        name_entry.bind("<KeyRelease>", lambda e: self.refresh_results())

        # Right panel: results
        right = ttk.Frame(main)
        main.add(right, weight=2)

        results = ttk.LabelFrame(right, text="Matching Files")
        results.pack(side=tk.TOP, fill=tk.BOTH, expand=True, padx=4, pady=4)

        cols = ("file", "exists")
        self.file_tree = ttk.Treeview(results, columns=cols, show="headings", selectmode="extended")
        self.file_tree.heading("file", text="File (absolute path)")
        self.file_tree.heading("exists", text="Exists")
        self.file_tree.column("file", width=600, anchor=tk.W)
        self.file_tree.column("exists", width=60, anchor=tk.CENTER)
        self.file_tree.pack(side=tk.TOP, fill=tk.BOTH, expand=True, padx=6, pady=6)
        self.file_tree.bind("<Double-1>", lambda e: self.on_open_selected())

        actions = ttk.Frame(results)
        actions.pack(side=tk.TOP, fill=tk.X, padx=6, pady=(0, 8))
        ttk.Button(actions, text="Open Selected", command=self.on_open_selected).pack(side=tk.LEFT)
        ttk.Button(actions, text="Reveal in Folder", command=self.on_reveal_selected).pack(side=tk.LEFT, padx=6)
        ttk.Button(actions, text="Copy Path", command=self.on_copy_path).pack(side=tk.LEFT, padx=6)

        # Status bar
        self.status_var = tk.StringVar(value="Ready")
        status = ttk.Label(self, textvariable=self.status_var, anchor=tk.W, relief=tk.SUNKEN)
        status.pack(side=tk.BOTTOM, fill=tk.X)

    def _configure_layout(self) -> None:
        self.update_idletasks()

    # ---------- Menu commands ----------
    def on_open_db(self) -> None:
        path = filedialog.askopenfilename(
            title="Open Tag DB (JSON)",
            filetypes=[("JSON files", "*.json"), ("All files", "*.*")],
        )
        if path:
            self._load_db_safely(path)

    def on_reload_db(self) -> None:
        if not self.db.json_path:
            messagebox.showinfo("Reload DB", "No database file loaded yet.")
            return
        self._load_db_safely(self.db.json_path)

    def on_quit(self) -> None:
        self.destroy()

    # ---------- Actions ----------
    def on_add_selected_tags(self) -> None:
        cat = self.category_cmb.get().strip()
        if not cat:
            messagebox.showwarning("No Category", "Please choose a category first.")
            return
        sels = self.tag_list.curselection()
        if not sels:
            messagebox.showwarning("No Tag", "Please select one or more tags to add.")
            return
        added = 0
        for i in sels:
            tag_name = self.tag_list.get(i)
            tk_pair: TagKey = (cat, tag_name)
            if tk_pair not in self.selected_filters:
                self.selected_filters.append(tk_pair)
                self.filter_tree.insert("", tk.END, values=tk_pair)
                added += 1
        if added:
            self.refresh_results()

    def on_remove_selected_filters(self) -> None:
        sels = self.filter_tree.selection()
        if not sels:
            return
        for item_id in sels:
            vals = self.filter_tree.item(item_id, "values")
            if len(vals) >= 2:
                tk_pair = (vals[0], vals[1])
                if tk_pair in self.selected_filters:
                    self.selected_filters.remove(tk_pair)
            self.filter_tree.delete(item_id)
        self.refresh_results()

    def on_clear_filters(self) -> None:
        self.selected_filters.clear()
        for iid in self.filter_tree.get_children():
            self.filter_tree.delete(iid)
        self.refresh_results()

    def on_open_selected(self) -> None:
        paths = self._selected_paths()
        for p in paths:
            open_with_system(p)

    def on_reveal_selected(self) -> None:
        paths = self._selected_paths()
        for p in paths:
            folder = os.path.dirname(p) if os.path.isfile(p) else p
            if not folder:
                folder = p
            open_with_system(folder)

    def on_copy_path(self) -> None:
        paths = self._selected_paths()
        if paths:
            self.clipboard_clear()
            self.clipboard_append("\n".join(paths))
            self.status_var.set(f"Copied {len(paths)} path(s) to clipboard.")

    # ---------- Helpers ----------
    def _selected_paths(self) -> List[str]:
        sels = self.file_tree.selection()
        paths = []
        for iid in sels:
            vals = self.file_tree.item(iid, "values")
            if vals:
                paths.append(vals[0])
        return paths

    def _load_db_safely(self, path: str) -> None:
        try:
            self.db.load(path)
        except Exception as e:
            messagebox.showerror("Load Failed", f"Could not load database:\n{path}\n\n{e}\n\n{traceback.format_exc()}")
            return
        self.db_path_var.set(path)
        self._refresh_categories()
        self._refresh_tag_list()
        self.refresh_results()
        self.status_var.set(f"Loaded DB: {path}")

    def _refresh_categories(self) -> None:
        cats = self.db.categories()
        self.category_cmb["values"] = cats
        if cats:
            self.category_cmb.current(0)
        else:
            self.category_cmb.set("")

    def _refresh_tag_list(self) -> None:
        self.tag_list.delete(0, tk.END)
        cat = self.category_cmb.get().strip()
        if not cat:
            return
        for t in self.db.tags_in_category(cat):
            self.tag_list.insert(tk.END, t)

    def refresh_results(self) -> None:
        # Clear tree
        for iid in self.file_tree.get_children():
            self.file_tree.delete(iid)

        name_sub = self.name_filter_var.get().strip()
        mode = self.mode_var.get()
        idxs = self.db.find_files(self.selected_filters, mode=mode, filename_substring=name_sub)
        for i in idxs:
            entry = self.db.get_entry_by_index(i)
            exists = "Yes" if self.db.exists(i) else "No"
            self.file_tree.insert("", tk.END, values=(entry.path, exists))
        self.status_var.set(f"{len(idxs)} file(s) matched.")

def main() -> None:
    # Optional: accept a --db path argument for convenience
    db_path: Optional[str] = None
    args = sys.argv[1:]
    if len(args) >= 2 and args[0] in ("--db", "-d"):
        db_path = args[1]
    app = TagFileBrowser(db_path=db_path)
    app.mainloop()


if __name__ == "__main__":
    main()
