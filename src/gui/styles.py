"""Dark-theme stylesheets shared across the application."""

MAIN_WINDOW = """
    QMainWindow           { background: #1E1E1E; }
    QSplitter::handle     { background: #3C3C3C; }
    QMenuBar              { background: #3C3C3C; color: #CCCCCC; }
    QMenuBar::item        { padding: 4px 10px; }
    QMenuBar::item:selected { background: #094771; }
    QMenu                 { background: #252526; color: #CCCCCC; border: 1px solid #454545; }
    QMenu::item           { padding: 4px 20px; }
    QMenu::item:selected  { background: #094771; }
    QMenu::separator      { height: 1px; background: #3C3C3C; margin: 2px 0; }
    QDockWidget::title    {
        background: #333333; color: #CCCCCC;
        padding: 4px 6px; font-size: 12px;
    }
    QDockWidget           { color: #CCCCCC; }
    QStatusBar            { background: #007ACC; color: #FFFFFF; font-size: 12px; }
    QStatusBar::item      { border: none; }
"""
