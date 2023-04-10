import random

def select_titles(titles, num_rounds):
    selected_titles = []
    for i in range(num_rounds):
        title = random.choice(titles)
        if title not in selected_titles:
            selected_titles.append(title)
    return selected_titles



def build_menu(buttons, n_cols, header_buttons=None, footer_buttons=None):
    menu = [buttons[i:i + n_cols] for i in range(0, len(buttons), n_cols)]
    if header_buttons:
        menu.insert(0, header_buttons)
    if footer_buttons:
        menu.append(footer_buttons)
    return menu


