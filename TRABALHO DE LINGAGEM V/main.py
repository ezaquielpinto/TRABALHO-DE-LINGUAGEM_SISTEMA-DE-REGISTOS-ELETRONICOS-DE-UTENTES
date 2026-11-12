import sqlite3
import unicodedata
from datetime import datetime


FORMATO_DATA = "%d-%m-%Y"
FORMATO_BD = "%Y-%m-%d"

SEXOS = {
    "M": "Masculino (M)",
    "F": "Feminino (F)",
    "X": "Outro (X)"
}


class BaseDados:
    def __init__(self, nome_bd="sreu.db"):
        self.conexao = sqlite3.connect(nome_bd)
        self.conexao.execute("PRAGMA foreign_keys = ON")
        self.cursor = self.conexao.cursor()
        self.criar_tabelas()

    def criar_tabelas(self):
        self.cursor.execute("""
            CREATE TABLE IF NOT EXISTS utentes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                numero_registo TEXT UNIQUE,
                nome TEXT NOT NULL,
                nascimento TEXT,
                sexo TEXT,
                nif TEXT,
                telefone TEXT,
                endereco TEXT
            )
        """)

        self.cursor.execute("""
            CREATE TABLE IF NOT EXISTS consultas (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                id_utente INTEGER NOT NULL,
                data_consulta TEXT NOT NULL,
                diagnostico TEXT NOT NULL,
                observacoes TEXT,
                FOREIGN KEY (id_utente) REFERENCES utentes(id)
            )
        """)
        self.conexao.commit()

    @staticmethod
    def gerar_numero_registo(nome, id_utente):
        ano = datetime.now().year
        nome_limpo = unicodedata.normalize("NFD", nome)
        nome_limpo = "".join(
            c for c in nome_limpo
            if unicodedata.category(c) != "Mn"
        )
        partes = nome_limpo.strip().split()
        primeiro_nome = partes[0] if partes else "UTENTE"
        iniciais = "".join(c for c in primeiro_nome if c.isalpha())[:3].upper()
        iniciais = iniciais.ljust(3, "X")
        return f"{ano}-{iniciais}-{id_utente:04d}"

    def registar_utente(self, nome, nascimento, sexo, nif, telefone, endereco):
        try:
            self.cursor.execute("""
                INSERT INTO utentes
                (nome, nascimento, sexo, nif, telefone, endereco)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (nome, nascimento, sexo, nif, telefone, endereco))

            id_utente = self.cursor.lastrowid
            numero = self.gerar_numero_registo(nome, id_utente)

            self.cursor.execute("""
                UPDATE utentes SET numero_registo = ? WHERE id = ?
            """, (numero, id_utente))

            self.conexao.commit()
            return numero
        except sqlite3.Error:
            self.conexao.rollback()
            raise

    def pesquisar_utente(self, numero):
        self.cursor.execute("""
            SELECT id, numero_registo, nome, nascimento, sexo,
                   nif, telefone, endereco
            FROM utentes
            WHERE numero_registo = ?
        """, (numero,))
        return self.cursor.fetchone()

    def listar_utentes(self):
        self.cursor.execute("""
            SELECT id, numero_registo, nome, nascimento, sexo,
                   nif, telefone, endereco
            FROM utentes
            ORDER BY id
        """)
        return self.cursor.fetchall()

    def atualizar_utente(self, id_utente, nome, nascimento, sexo,
                         nif, telefone, endereco):
        try:
            self.cursor.execute("""
                UPDATE utentes
                SET nome = ?, nascimento = ?, sexo = ?, nif = ?,
                    telefone = ?, endereco = ?
                WHERE id = ?
            """, (nome, nascimento, sexo, nif, telefone, endereco, id_utente))
            self.conexao.commit()
            return self.cursor.rowcount > 0
        except sqlite3.Error:
            self.conexao.rollback()
            raise

    def eliminar_utente(self, id_utente):
        try:
            self.cursor.execute(
                "DELETE FROM consultas WHERE id_utente = ?", (id_utente,)
            )
            self.cursor.execute("DELETE FROM utentes WHERE id = ?", (id_utente,))
            eliminado = self.cursor.rowcount > 0
            self.conexao.commit()
            return eliminado
        except sqlite3.Error:
            self.conexao.rollback()
            return False

    def registar_consulta(self, id_utente, data, diagnostico, observacoes):
        try:
            self.cursor.execute("""
                INSERT INTO consultas
                (id_utente, data_consulta, diagnostico, observacoes)
                VALUES (?, ?, ?, ?)
            """, (id_utente, data, diagnostico, observacoes))
            self.conexao.commit()
        except sqlite3.Error:
            self.conexao.rollback()
            raise

    def historico_clinico(self, id_utente):
        self.cursor.execute("""
            SELECT data_consulta, diagnostico, observacoes
            FROM consultas
            WHERE id_utente = ?
            ORDER BY data_consulta DESC, id DESC
        """, (id_utente,))
        return self.cursor.fetchall()

    def fechar(self):
        self.conexao.close()


class SistemaUtentes:
    def __init__(self):
        self.bd = BaseDados()

    @staticmethod
    def converter_data_para_bd(data):
        """Recebe DD-MM-AAAA e devolve AAAA-MM-DD para guardar no SQLite."""
        try:
            return datetime.strptime(data, FORMATO_DATA).strftime(FORMATO_BD)
        except ValueError:
            return None

    @staticmethod
    def apresentar_data(data):
        """Apresenta datas novas e antigas no formato DD-MM-AAAA."""
        if not data:
            return "Não informado"

        for formato in (FORMATO_BD, FORMATO_DATA):
            try:
                return datetime.strptime(data, formato).strftime(FORMATO_DATA)
            except ValueError:
                pass
        return data

    @staticmethod
    def normalizar_sexo(sexo):
        valor = (sexo or "").strip().upper()
        equivalencias = {
            "M": "M", "MASCULINO": "M", "MASCULINO (M)": "M",
            "F": "F", "FEMININO": "F", "FEMININO (F)": "F",
            "X": "X", "OUTRO": "X", "OUTRA": "X", "OUTRO (X)": "X"
        }
        codigo = equivalencias.get(valor)
        return SEXOS.get(codigo) if codigo else None

    @staticmethod
    def imprimir_utente(utente):
        print("\n" + "=" * 55)
        print("             FICHA COMPLETA DO PACIENTE")
        print("=" * 55)
        print(f"ID interno:       {utente[0]}")
        print(f"Número de registo:{utente[1]}")
        print(f"Nome completo:    {utente[2]}")
        print(f"Data de nascimento: {SistemaUtentes.apresentar_data(utente[3])}")
        print(f"Sexo:             {SistemaUtentes.normalizar_sexo(utente[4]) or 'Não informado'}")
        print(f"NIF:              {utente[5] or 'Não informado'}")
        print(f"Telefone:         {utente[6] or 'Não informado'}")
        print(f"Endereço:         {utente[7] or 'Não informado'}")
        print("=" * 55)

    def pedir_data(self, mensagem, obrigatoria=False, permitir_futura=False):
        while True:
            data = input(mensagem).strip()
            if not data and not obrigatoria:
                return ""
            data_bd = self.converter_data_para_bd(data)
            if data_bd is None:
                print("Data inválida. Utilize o formato DIA-MÊS-ANO.")
                continue
            data_obj = datetime.strptime(data_bd, FORMATO_BD).date()
            if not permitir_futura and data_obj > datetime.now().date():
                print("A data não pode ser posterior à data atual.")
                continue
            return data_bd

    def pedir_sexo(self, mensagem="Sexo (M/F/X): "):
        while True:
            sexo = self.normalizar_sexo(input(mensagem))
            if sexo:
                return sexo
            print("Opção inválida. Introduza M (Masculino), F (Feminino) ou X (Outro).")

    def cadastrar(self):
        print("\n========== REGISTO DE PACIENTE ==========")
        nome = input("Nome completo: ").strip()
        if not nome:
            print("ERRO: O nome é obrigatório.")
            return

        nascimento = self.pedir_data(
            "Data de nascimento (DD-MM-AAAA; ENTER se desconhecida): "
        )
        sexo = self.pedir_sexo()
        nif = input("NIF (opcional): ").strip()
        telefone = input("Telefone: ").strip()
        endereco = input("Endereço: ").strip()

        try:
            numero = self.bd.registar_utente(
                nome, nascimento, sexo, nif, telefone, endereco
            )
            print("\nPACIENTE REGISTADO COM SUCESSO!")
            print("Número de registo:", numero)
        except sqlite3.Error as erro:
            print("Não foi possível registar o paciente:", erro)

    def pesquisar(self):
        print("\n========== PESQUISAR PACIENTES ==========")
        numero = input("Introduza o número de registo: ").strip()
        utente = self.bd.pesquisar_utente(numero)

        if utente:
            self.imprimir_utente(utente)
            consultas = self.bd.historico_clinico(utente[0])
            print(f"Consultas registadas: {len(consultas)}")
        else:
            print("Paciente não encontrado.")

    def listar(self):
        print("\n========== LISTA COMPLETA DE PACIENTES REGISTADOS ==========")
        utentes = self.bd.listar_utentes()

        if not utentes:
            print("Não existem utentes registados.")
            return

        print(f"Total de utentes: {len(utentes)}")
        for utente in utentes:
            self.imprimir_utente(utente)

    def atualizar(self):
        print("\n========== ATUALIZAR DADOS ==========")
        numero = input("Número de registo do paciente: ").strip()
        utente = self.bd.pesquisar_utente(numero)

        if not utente:
            print("Paciente não encontrado.")
            return

        self.imprimir_utente(utente)
        print("\nPressione ENTER para manter cada valor atual.")

        nome = input(f"Novo nome [{utente[2]}]: ").strip() or utente[2]

        nascimento_atual = self.apresentar_data(utente[3])
        nascimento_input = input(
            f"Nova data de nascimento [{nascimento_atual}] (DD-MM-AAAA): "
        ).strip()
        if nascimento_input:
            nascimento = self.converter_data_para_bd(nascimento_input)
            if not nascimento:
                print("Data inválida. Atualização cancelada.")
                return
            if datetime.strptime(nascimento, FORMATO_BD).date() > datetime.now().date():
                print("A data de nascimento não pode ser futura. Por favor, insira uma data valida!")
                return
        else:
            nascimento = utente[3] or ""

        sexo_input = input(
            f"Novo sexo [atual: {self.normalizar_sexo(utente[4]) or 'Não informado'}] (M/F/X): "
        ).strip()
        if sexo_input:
            sexo = self.normalizar_sexo(sexo_input)
            if not sexo:
                print("Sexo inválido. Atualização cancelada.")
                return
        else:
            sexo = self.normalizar_sexo(utente[4]) or ""

        nif = input(f"Novo NIF [{utente[5] or 'Não informado'}]: ").strip() or (utente[5] or "")
        telefone = input(f"Novo telefone [{utente[6] or 'Não informado'}]: ").strip() or (utente[6] or "")
        endereco = input(f"Novo endereço [{utente[7] or 'Não informado'}]: ").strip() or (utente[7] or "")

        try:
            atualizado = self.bd.atualizar_utente(
                utente[0], nome, nascimento, sexo, nif, telefone, endereco
            )
            if atualizado:
                print("Dados atualizados com sucesso.")
                print("Número de registo mantido:", utente[1])
            else:
                print("Nenhum registo foi alterado.")
        except sqlite3.Error as erro:
            print("Erro ao atualizar os dados:", erro)

    def eliminar(self):
        print("\n========== ELIMINAR PACIENTE ==========")
        numero = input("Número de registo do paciente: ").strip()
        utente = self.bd.pesquisar_utente(numero)

        if not utente:
            print("Paciente não encontrado.")
            return

        self.imprimir_utente(utente)
        print("\nATENÇÃO: esta operação elimina também o histórico clínico associado.")
        confirmacao = input("Digite SIM para confirmar a eliminação: ").strip().upper()

        if confirmacao == "SIM":
            if self.bd.eliminar_utente(utente[0]):
                print("Paciente eliminado.")
            else:
                print("Não foi possível eliminar o paciente.")
        else:
            print("Operação cancelada.")

    def consulta(self):
        print("\n========== REGISTAR CONSULTA ==========")
        numero = input("Número de registo do paciente: ").strip()
        utente = self.bd.pesquisar_utente(numero)

        if not utente:
            print("paciente não encontrado.")
            return

        print(f"Paciente: {utente[2]} | Registo: {utente[1]}")
        data = self.pedir_data("Data da consulta (DD-MM-AAAA): ", obrigatoria=True)
        diagnostico = input("Diagnóstico: ").strip()
        if not diagnostico:
            print("O diagnóstico é obrigatório.")
            return
        observacoes = input("Observações clínicas (opcional): ").strip()

        try:
            self.bd.registar_consulta(
                utente[0], data, diagnostico, observacoes
            )
            print("Consulta registada com sucesso.")
        except sqlite3.Error as erro:
            print("Erro ao registar consulta:", erro)

    def historico(self):
        print("\n========== HISTÓRICO CLÍNICO ==========")
        numero = input("Número de registo: ").strip()
        utente = self.bd.pesquisar_utente(numero)

        if not utente:
            print("paciente não encontrado.")
            return

        self.imprimir_utente(utente)
        consultas = self.bd.historico_clinico(utente[0])

        if not consultas:
            print("Este paciente ainda não possui consultas, por favor registe uma consulta!")
            return

        for i, consulta in enumerate(consultas, start=1):
            print("\n" + "-" * 45)
            print(f"CONSULTA N.º {i}")
            print("Data:", self.apresentar_data(consulta[0]))
            print("Diagnóstico:", consulta[1])
            print("Observações:", consulta[2] or "Sem observações")
        print("-" * 45)

    def menu(self):
        try:
            while True:
                print("\n" + "=" * 55)
                print("       SISTEMA DE REGISTO ELETRÓNICO DE UTENTES")
                print("=" * 55)
                print("1 - Registar novo paciente")
                print("2 - Pesquisar pacientes registrados")
                print("3 - Listar todos os pacientes")
                print("4 - Registar consulta médica")
                print("5 - Consultar histórico clínico de pacientes")
                print("6 - Atualizar dados do paciente")
                print("7 - Eliminar paciente")
                print("0 - Encerrar sistema")
                print("=" * 55)

                opcao = input("Escolha uma opção: ").strip()

                if opcao == "1":
                    self.cadastrar()
                elif opcao == "2":
                    self.pesquisar()
                elif opcao == "3":
                    self.listar()
                elif opcao == "4":
                    self.consulta()
                elif opcao == "5":
                    self.historico()
                elif opcao == "6":
                    self.atualizar()
                elif opcao == "7":
                    self.eliminar()
                elif opcao == "0":
                    print("Sistema encerrado.")
                    break
                else:
                    print("Opção inválida. Tente novamente.")
        finally:
            self.bd.fechar()


if __name__ == "__main__":
    sistema = SistemaUtentes()
    sistema.menu()
