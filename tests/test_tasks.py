"""Testes do Encrypted-Task-Manager (sem terminal interativo)."""
import os
import shutil
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# dados em diretório temporário (nunca em ~/Documents)
_TMP = tempfile.mkdtemp(prefix="etm_test_")
os.environ["TAREFAS_DIR"] = _TMP

from src.storage import load_index, task_dir
from src.tasks import (
    WrongPassword,
    create_task_values,
    delete_task,
    edit_task_values,
    list_tasks,
)

PW = "senha-mestra-teste"


def _fresh():
    """Zera o diretório de dados entre testes."""
    for fname in os.listdir(task_dir()):
        os.remove(os.path.join(task_dir(), fname))


def test_crud_flow():
    _fresh()
    tid = create_task_values(PW, "Comprar café", "Coadernado 500g torra escura")
    tid2 = create_task_values(PW, "Estudar cripto", "AES + Scrypt")
    tasks = list_tasks(PW)
    assert len(tasks) == 2
    assert tasks[0]["nome"] == "Comprar café"
    assert tasks[0]["desc"] == "Coadernado 500g torra escura"

    # edição (restauração da função "Editar" do monolito original)
    edit_task_values(PW, tid, name="Comprar café especial", concluida=True)
    tasks = list_tasks(PW)
    t = next(x for x in tasks if x["id"] == tid)
    assert t["nome"] == "Comprar café especial"
    assert t["concluida"] is True
    assert t["desc"] == "Coadernado 500g torra escura"  # desc mantida

    # exclusão
    assert delete_task(tid) is True
    assert delete_task(tid) is False
    tasks = list_tasks(PW)
    assert len(tasks) == 1 and tasks[0]["id"] == tid2
    assert delete_task(tid2) is True


def test_wrong_password():
    _fresh()
    create_task_values(PW, "Segredo", "conteudo confidencial")
    try:
        list_tasks("senha-errada")
        raise AssertionError("senha errada deveria falhar")
    except WrongPassword:
        pass


def test_content_is_encrypted_on_disk():
    _fresh()
    create_task_values(PW, "TopSecretName", "TopSecretDesc 12345")
    for fname in os.listdir(task_dir()):
        if fname.endswith(".taf"):
            raw = open(os.path.join(task_dir(), fname), encoding="utf-8").read()
            assert "TopSecret" not in raw, "conteúdo em claro no disco!"
            break
    else:
        raise AssertionError("nenhum .taf criado")
    idx = open(os.path.join(task_dir(), "tarefas.json"), encoding="utf-8").read()
    assert "TopSecret" not in idx


def test_validation():
    try:
        create_task_values(PW, "", "x")
        raise AssertionError("nome vazio deveria falhar")
    except ValueError:
        pass
    try:
        create_task_values(PW, "n" * 51, "x")
        raise AssertionError("nome longo deveria falhar")
    except ValueError:
        pass


def test_corrupt_index_resilient():
    _fresh()
    with open(os.path.join(task_dir(), "tarefas.json"), "w") as f:
        f.write("{not json!!")
    assert load_index() == []
    create_task_values(PW, "após-corrupção", "ok")
    assert len(load_index()) == 1


if __name__ == "__main__":
    fns = [v for k, v in sorted(globals().items()) if k.startswith("test_")]
    for fn in fns:
        fn()
        print(f"✅ {fn.__name__}")
    print(f"\n{len(fns)} testes passaram.")
    shutil.rmtree(_TMP, ignore_errors=True)
