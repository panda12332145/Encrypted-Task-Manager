"""TUI portátil (só input/print — funciona em Windows, Linux e macOS,
sem privilégios de root e sem dependências externas de teclado)."""
import os

from .tasks import prompt_create, prompt_delete, prompt_edit, prompt_list

CLEAR = "cls" if os.name == "nt" else "clear"

OPTIONS = [
    "Criar Nova Tarefa",
    "Ver Tarefas",
    "Editar Tarefa",
    "Excluir Tarefa",
    "Sair",
]


def draw_menu():
    os.system(CLEAR)
    print("=" * 34)
    print("   🗂️  Gerenciador de Tarefas (criptografado)")
    print("=" * 34)
    for i, opt in enumerate(OPTIONS, 1):
        print(f"  {i}. {opt}")
    print("-" * 34)


def run(password: str):
    actions = {
        "1": lambda: prompt_create(password),
        "2": lambda: prompt_list(password),
        "3": lambda: prompt_edit(password),
        "4": lambda: prompt_delete(password),
    }
    while True:
        draw_menu()
        choice = input("Escolha [1-5]: ").strip()
        if choice == "5":
            print("👋 Até logo!")
            break
        if choice in actions:
            actions[choice]()
            input("\nPressione Enter para continuar...")
        else:
            print("❌ Opção inválida.")
            input("Pressione Enter para continuar...")
