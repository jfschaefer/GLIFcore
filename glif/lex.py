"""
   parsing Lex Dateien
"""

import os.path

from . import parsing
from .utils import Result

from enum import auto, Enum
from pydantic import BaseModel

# from lexicon.data_classes import Format
# from lexicon.data_classes import Importer

DEFAULT_ARCHIVE = "tmpGLIF/default/test_build"
KOMMENTAR_ZEICHEN = "#"
DEFAULT_PATH = "."
# TODO Path in die Eingabe vohin die erstellten Dateien kommen sollen.


class Type(BaseModel):
    """
    Einzelne simple Typ-Definitionen
    """

    single_type: str


class Definition(BaseModel):
    """
    Die Definition eines Objektes.
    """

    name: str
    type_: list[Type]
    lang: str = "Eng"


class Format(Enum):
    """
    mögliche Import-Formate
    """

    GF_RESOURCE = auto()
    MMT_TYPE = auto()
    MMT_VIEW = auto()


class Importer(BaseModel):
    """
    Ein konkreter Import. Hierfür wird der Link mit dem
    entsprechenden Format abgespeichert
    """

    link: str
    format_: Format

class LexiconParser(object):
    # definition_list: Paare von (name, typ), name: str und typ: list(str)
    # Hier befinden sich die eigentlichen Definitionen der Objekte.
    definition_list: list[Definition] = []

    # Liste mit jeglichen (auch komplexeren) vorhanden Typ-Definitionen
    # type_def_list beinhaltet alle Typdefinitionen, also auch die,
    # die mit ⟶ von kleineren Typen aufgebaut ist.
    # Beispiel: VP : \iota ⟶ o
    # (Liste statt Dict, weil Type nicht gehasht werden kann)
    type_def_list: list[tuple[Type, str]] = []

    # Dateien, die in gf oder mmt importiert werden müssen.
    import_files: list[Importer] = []

    archive: str = DEFAULT_ARCHIVE
    archive_subdir: str = ""
    logs: list[str] = []
    lexicon_name: str
    lexicon_path: str
    cwd: str = DEFAULT_PATH

    def __init__(
        self,
        lexicon_path: str,
        archive: str = DEFAULT_ARCHIVE,
        subdir: str = "",
        cwd: str = DEFAULT_PATH,
    ) -> None:
        """
        Nimmt einem Pfad zu einer Lexicondatei an und optional das Archive Verzeichnis.
        Bereitet alles für die Erstellung der GF und MMT Dateien vor.
        """
        # TODO Eingabe überprüfen
        self.definition_list = []
        self.type_def_list = []
        self.import_files = []
        self.archive = archive
        self.archive_subdir = subdir
        self.logs = []
        self.lexicon_path = lexicon_path
        self.cwd = cwd

        code: str = ""
        with open(lexicon_path, "r", encoding="UTF-8") as flex:
            code = flex.read()

        # Löschen der Kommentare
        codelines: list[str] = []
        for line in code.split("\n"):
            if line.split(KOMMENTAR_ZEICHEN)[0].strip():
                codelines.append(line.split("#")[0].strip())
        if codelines == []:
            raise RuntimeError("Found no codelines")
        self.lexicon_name = codelines[0].split()[1]

        if codelines[0].split()[0] != "Lexicon":
            raise RuntimeError("A lexicon file have to start with 'Lexicon'")
        if not self.lexicon_name.isidentifier():
            raise RuntimeError("Lexicon name have to be a identifier")

        typdef = True
        for line in codelines[1:]:
            if typdef:
                if line.strip() == "def":
                    typdef = False
                    continue
                if line.startswith("include"):  # Veraussetzung zum Import ist Endung
                    result = self.include_handle(line)
                    if not result.success:
                        raise RuntimeError(result.logs)
                else:
                    name_type, type_name = line.split(":")
                    name_type = name_type.strip()
                    type_name = type_name.replace(" ", "")
                    type_ = Type(single_type=name_type)
                    # TODO überprüfen, dass ein Typ nicht schon vorhanden ist.
                    self.type_def_list.append((type_, type_name))
            else:
                name, full_types = line.split(":")
                line_type = full_types.replace(" ", "").split("->")
                line_type_list: list[Type] = []
                for type_str in line_type:
                    line_type_list.append(Type(single_type=type_str))
                self.definition_list.append(
                    Definition(name=name.strip(), type_=line_type_list)
                )

    def include_handle(self, line: str) -> Result[str]:
        """
        Überprüft die include Datei um das passende Format zu erkennen
        Der Pfad ist immer in Abhängigkeit von der lex Datei anzugeben.
        """
        import_file_name = line.split()[1]
        ending = import_file_name.split(".")[-1]
        lexicon_dir_path = os.path.dirname(self.lexicon_path)
        import_file_path = os.path.join(lexicon_dir_path, import_file_name)
        if ending == "gf":
            # Überprüfung ob es sich bei der gf Datei um ein resource handelt
            with open(import_file_path, "r") as import_file:
                file_r = parsing.identify_file(import_file.read())
                if file_r.success:
                    if file_r.value[0] == "gf-resource":
                        importer = Importer(
                            link=import_file_path, format_=Format.GF_RESOURCE
                        )
                        self.import_files.append(importer)
                    else:
                        return Result(
                            False,
                            None,
                            f"{import_file_name} is not a gf-resource file "
                            + "or a mmt file",
                        )
        elif ending == "mmt":
            with open(import_file_path, "r") as import_file:
                file_r = parsing.identify_file(import_file.read())
                if file_r.success:
                    if file_r.value[0] == "mmt-view":
                        importer = Importer(
                            link=import_file_path, format_=Format.MMT_VIEW
                        )
                        self.import_files.append(importer)
                    elif "mmt" in file_r.value[0]:
                        importer = Importer(
                            link=import_file_path, format_=Format.MMT_TYPE
                        )
                        self.import_files.append(importer)
                    else:
                        return Result(
                            False,
                            None,
                            f"{import_file_name} is not a gf-resource file "
                            + "or a mmt file",
                        )
        return Result(True, "\n")

    def create_gf_abstract(self) -> None:
        """
        Erstellst die Datei GF abstract mit dem {self.lexicon_name}.gf als Namen
        """
        auto_comm_gf = "-- This is auto-generated. Pls do not modify.\n"
        write_name: str = os.path.join(self.cwd, f"{self.lexicon_name}.gf")
        if self.file_check(write_name, auto_comm_gf):
            with open(write_name, "w", encoding="UTF-8") as gfabs:
                gfabs.write(auto_comm_gf)
                gfabs.write(f"abstract {self.lexicon_name} = " + "{\n")

                # die vorhandenen Typen
                gfabs.write("\tcat\n")
                for typ, _ in self.type_def_list:
                    gfabs.write(f"\t\t{typ.single_type};\n")

                gfabs.write("\tfun\n")
                for definition in self.definition_list:
                    gfabs.write(f"\t\t{definition.name} : ")
                    final_type: str = ""
                    for typ in definition.type_:
                        final_type += typ.single_type + " -> "
                    final_type = final_type[:-4]
                    gfabs.write(f"{final_type};\n")

                gfabs.write("}")

    def create_gf_lincat_concrete(self) -> None:
        """
        Erstellt die GF Lincat Concrete Datei mit dem Namen
        {self.lexicon_name}LincatCon.gf
        """

        auto_comm_lincatcon = "-- This is auto-generated. Pls do not modify.\n"
        write_name: str = os.path.join(self.cwd, f"{self.lexicon_name}LincatCon.gf")
        if self.file_check(write_name, auto_comm_lincatcon):
            with open(write_name, "w", encoding="UTF-8") as gflincatcon:
                gflincatcon.write(auto_comm_lincatcon)
                gflincatcon.write(
                    f"concrete {self.lexicon_name}LincatCon of {self.lexicon_name} = "
                    + "{\n"
                )
                gflincatcon.write("\tlincat\n")
                for typ, _ in self.type_def_list:
                    gflincatcon.write(f"\t\t{typ.single_type} = Str;\n")
                gflincatcon.write("}")

    def create_gf_concrete(self) -> None:
        """
        Erstellt die GF concrete Datei mit {self.lexicon_name}Eng.gf als Namen
        """
        # default englishFile
        auto_comm_eng = "-- This is auto-generated. Pls do not modify.\n"
        write_name: str = os.path.join(self.cwd, f"{self.lexicon_name}Eng.gf")
        if self.file_check(write_name, auto_comm_eng):
            with open(write_name, "w", encoding="UTF-8") as gfcon:
                gfcon.write(auto_comm_eng)

                open_needed: bool = False
                for importer in self.import_files:
                    if importer.format_ == Format.GF_RESOURCE:
                        open_needed = True
                        break

                if open_needed:
                    opened_resources = ""
                    for importer in self.import_files:
                        if importer.format_ == Format.GF_RESOURCE:
                            import_name = os.path.basename(importer.link[:-3])
                            opened_resources += import_name + ", "
                    opened_resources = opened_resources[:-2]
                    gfcon.write(
                        f"concrete {self.lexicon_name}Eng of {self.lexicon_name} "
                        + f"= {self.lexicon_name}LincatCon ** "
                        + f"open {opened_resources} in "
                        + "{\n"
                    )
                else:
                    gfcon.write(
                        f"concrete {self.lexicon_name}Eng of {self.lexicon_name} "
                        + f"= {self.lexicon_name}LincatCon ** "
                        + "{\n"
                    )

                gfcon.write("\tlin\n")
                for definition in self.definition_list:
                    if len(definition.type_) == 1:
                        # nur Wörter der Form "Peter : Name"
                        gfcon.write(
                            f"\t\t{definition.name} = "
                            + f"mk{definition.type_[0].single_type} "
                            + f'"{definition.name}";\n'
                        )

                gfcon.write("}")

    def create_mmt_semantics(self) -> None:
        """
        Erstellt die MMT Datei mit den Semantics, die später im view verwendet wird.
        """
        auto_comm_sem = "// This is auto-generated. Pls do not modify.❚\n"
        write_name: str = os.path.join(self.cwd, f"{self.lexicon_name}Semantics.mmt")
        if self.file_check(write_name, auto_comm_sem):
            with open(write_name, "w", encoding="UTF-8") as mmtsem:
                mmtsem.write(auto_comm_sem)
                mmtsem.write(
                    f"namespace http://mathhub.info/{self.archive}"
                    + f"{'/' + self.archive_subdir if self.archive_subdir else '' } ❚\n"
                )
                mmtsem.write(f"theory {self.lexicon_name}Semantics : ur:?LF =\n")

                for importer in self.import_files:
                    if importer.format_ == Format.MMT_TYPE:
                        import_name = os.path.basename(importer.link[:-4])
                        mmtsem.write(f"\tinclude ?{import_name} ❙\n")

                for definition in self.definition_list:
                    mmt_definition_type: str = ""
                    for type_, type_name in self.type_def_list:
                        if type_ == definition.type_[0]:
                            mmt_definition_type = type_name
                    mmtsem.write(
                        f"\t{definition.name} :" + f" {mmt_definition_type} ❙\n"
                    )
                mmtsem.write("❚")

    def create_mmt_sem_constr(self) -> None:
        """
        Erstellt die MMT Datei, die den view von der erstellten GF abstract
        zur MMT Semantics beinhaltet.
        """
        auto_comm_semcon = "// This is auto-generated. Pls do not modify.❚\n"
        write_name: str = os.path.join(self.cwd, f"{self.lexicon_name}SemConstr.mmt")
        if self.file_check(write_name, auto_comm_semcon):
            with open(write_name, "w", encoding="UTF-8") as mmtsemcon:
                mmtsemcon.write(auto_comm_semcon)
                mmtsemcon.write(
                    f"namespace http://mathhub.info/{self.archive}"
                    + f"{'/' + self.archive_subdir if self.archive_subdir else ''}/ ❚\n"
                )
                mmtsemcon.write(
                    f"view {self.lexicon_name}SemConstr : "
                    + f"http://mathhub.info/{self.archive}/"
                    + f"{self.archive_subdir + '/' if self.archive_subdir else ''}"
                    + f"{self.lexicon_name}.gf?{self.lexicon_name} "
                    + f"-> ?{self.lexicon_name}Semantics =\n"
                )

                for importer in self.import_files:
                    if importer.format_ == Format.MMT_VIEW:
                        mmtsemcon.write(f"\tinclude ?{importer.link[:-4]} ❙\n")

                for type_name, type_ in self.type_def_list:
                    mmtsemcon.write(f"\t{type_name.single_type} = {type_} ❙\n")

                for definition in self.definition_list:
                    if len(definition.type_) == 1:
                        mmtsemcon.write(f"\t{definition.name} = {definition.name} ❙\n")

                mmtsemcon.write("❚")

    def file_check(self, filename: str, auto_gen_text: str) -> bool:
        """
        Nimmt den Filenamen und den zu überprüfenden auto-gen Text und behandelt
        den Fall, dass eine Datei mit dem Filenamen schon existiert, der nicht
        automatisch generiert wurde.
        """
        file_path = os.path.join(self.cwd, filename)
        if os.path.isfile(file_path):
            with open(file_path, "r", encoding="UTF-8") as readfile:
                if readfile.readline() == auto_gen_text:
                    return True
                print("{filename} already exists and will not be overwritten")
                return False

        return True

    def get_lexicon_name(self) -> str:
        return self.lexicon_name

    def create_gf(self) -> None:
        self.create_gf_abstract()
        self.create_gf_lincat_concrete()
        self.create_gf_concrete()

    def create_mmt(self) -> None:
        self.create_mmt_semantics()
        self.create_mmt_sem_constr()

    def create_all(self) -> None:
        self.create_gf()
        self.create_mmt()
