"""
   parsing Lex Dateien
"""
import dataclasses
import os.path
import shlex

from glif import parsing
from glif.utils import Result

from enum import auto, Enum
# from pydantic import BaseModel

# from lexicon.data_classes import Format
# from lexicon.data_classes import Importer

DEFAULT_ARCHIVE = "tmpGLIF/default/test_build"
KOMMENTAR_ZEICHEN = "#"
DEFAULT_PATH = "."
# TODO Path in die Eingabe vohin die erstellten Dateien kommen sollen.
POSSIBLE_FLAGS_WORD = ["-l", "-add", "-drop"]
POSSIBLE_FLAGS_TYPE = ["-l", "-constr"]


@dataclasses.dataclass
class Type:
    """
    Einzelne simple Typ-Definitionen
    """

    single_type: str


@dataclasses.dataclass
class Type_Definition:
    """
    Type Definitionen mit MMT Form + Sprache und GF Sonderformen
    gf_forms -> tuple von (form, lang)
    """

    name: Type
    mmt_form: str
    gf_forms: list[tuple[str, str]] = dataclasses.field(default_factory=list)
    constructor: list[tuple[str, str]] = dataclasses.field(default_factory=list)


@dataclasses.dataclass
class Definition:
    """
    Die Definition eines Objektes.
    name: ist der Name des zu definierten Objekts und gleichzeitig die
        Englischen Definition
    type_: ist der jeweilige komplexe Typ der Definition.
    other_names: die Bedeutung des Objektes in anderen Sprachen, markiert
        mit der jeweiligen Sprache
    """

    name: str
    type_: list[Type]
    drop: bool = False  # True: Für alle Sprachen wird <name> nicht verwendet
    other_names: list[tuple[str, str]] = dataclasses.field(default_factory=list)  # tuples of (name, lang)
    to_add: str = ""


class Format(Enum):
    """
    mögliche Import-Formate
    """

    GF_ABSTRACT = auto()
    GF_RESOURCE = auto()
    GF_CONCRETE = auto()
    MMT_TYPE = auto()
    MMT_VIEW = auto()


@dataclasses.dataclass
class Importer:
    """
    Ein konkreter Import. Hierfür wird der Link mit dem
    entsprechenden Format abgespeichert.
    Beim Format GF_RESOURCE wird zudem die Sprache angegeben.
    """

    link: str
    format_: Format
    lang: str = "Eng"


class LexiconParser(object):
    # definition_list: Paare von (name, typ), name: str und typ: list(str)
    # Hier befinden sich die eigentlichen Definitionen der Objekte.
    # Der Default aller Sprachen/ füllt andere (als Eng) Sprachen auf falls
    # keine definition in der jeweiligen Sprache existiert
    definition_list: dict[str, Definition] = {}

    # Liste mit jeglichen (auch komplexeren) vorhanden Typ-Definitionen
    # type_def_list beinhaltet alle Typdefinitionen, also auch die,
    # die mit ⟶ von kleineren Typen aufgebaut ist.
    # Beispiel: VP : \iota ⟶ o
    # (Liste statt Dict, weil Type nicht gehasht werden kann)
    type_def_list: list[Type_Definition] = []

    # Dateien, die in gf oder mmt importiert werden müssen.
    import_files: list[Importer] = []

    archive: str = DEFAULT_ARCHIVE
    archive_subdir: str = ""
    logs: list[str] = []
    lexicon_name: str
    lexicon_path: str
    cwd: str = DEFAULT_PATH
    languages: list[str] = []
    create_cat: bool

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
        self.definition_list = {}
        self.type_def_list = []
        self.import_files = []
        self.archive = archive
        self.archive_subdir = subdir
        self.logs = []
        self.lexicon_path = lexicon_path
        self.cwd = cwd
        self.languages = ["Eng"]
        self.create_cat = True

        code: str = ""
        with open(lexicon_path, "r", encoding="UTF-8") as flex:
            code = flex.read()

        # Löschen der Kommentare
        codelines: list[str] = []
        for line in code.split("\n"):
            if line.split(KOMMENTAR_ZEICHEN)[0].strip():
                codelines.append(line.split("#")[0].strip())
        if not codelines:
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
                else:  # TODO das hier auslagern
                    line_split = line.split(":", 2)
                    if len(line_split) < 2:
                        raise RuntimeError(f"no seperator ':' in {line}\n")
                    name_type = line_split[0].strip()
                    type_name = line_split[1].replace(" ", "")
                    rest = ""
                    if len(line_split) == 3:
                        rest = line_split[2]
                    # options
                    current_option = ""
                    lang = ""
                    long_option = ""
                    gf_forms = []
                    constructor = []
                    for option in rest.split():
                        if current_option == "":
                            current_option = option
                        elif current_option == "-l":
                            if lang == "":
                                lang = option
                            elif option in POSSIBLE_FLAGS_TYPE:
                                # TODO schon in der Sprache vorhanden überprüfen
                                gf_forms.append((long_option.strip(), lang))
                                lang = ""
                                current_option = option
                                long_option = ""
                            else:
                                long_option += " " + option
                        elif current_option == "-constr":
                            if lang == "":
                                lang = option
                            else:
                                # TODO schon in der Sprache vorhanden überprüfen
                                constructor.append((option, lang))
                                current_option = ""
                                lang = ""
                        else:
                            raise RuntimeError("unknown flag or false flag usage\n")

                    if long_option != "":
                        if current_option == "-l" and lang != "":
                            gf_forms.append((long_option.strip(), lang))
                            current_option = ""
                            lang = ""
                            long_option = ""
                        else:  # Das sollte nie erreicht werden.
                            raise RuntimeError("Something went wrong\n")

                    if current_option != "":
                        raise RuntimeError("unknown flag or false flag usage\n")

                    for type_definition in self.type_def_list:
                        if name_type == type_definition.name.single_type:
                            raise RuntimeError(f"{name_type} already defined\n")
                    type_ = Type(single_type=name_type)
                    type_definition = Type_Definition(
                        name=type_,
                        mmt_form=type_name,
                        gf_forms=gf_forms,
                        constructor=constructor,
                    )
                    self.type_def_list.append(type_definition)
            else:
                name, full_types = line.split(":")
                name = name.strip()
                line_type = full_types.split("->")
                line_type_list: list[Type] = []
                for type_str in line_type[:-1]:
                    line_type_list.append(Type(single_type=type_str.strip()))

                # der letzte Typ + mögliche optionen
                type_and_ending = line_type[-1].split()
                line_type_list.append(Type(single_type=type_and_ending[0].strip()))

                options = type_and_ending[1:]
                other_names: list[tuple[str, str]] = []
                lang = ""
                to_add = ""
                current_option = ""
                long_option = ""
                drop = False
                for option in options:
                    if current_option == "":
                        current_option = option
                    elif current_option == "-l":
                        if lang == "":
                            lang = option
                            result = self.lang_handle(lang, name)
                            if not result.success:
                                raise RuntimeError(result.logs)
                        else:
                            if option in POSSIBLE_FLAGS_WORD:
                                if lang != "Eng":
                                    other_names.append((long_option.strip(), lang))
                                else:
                                    if to_add != "":
                                        raise RuntimeError(
                                            "special case of" + f" {name} already set\n"
                                        )
                                    to_add = long_option
                                lang = ""
                                long_option = ""
                                current_option = option
                            else:
                                long_option += " " + option
                    elif current_option == "-add":
                        if to_add != "":
                            raise RuntimeError(f"special case of {name} already set\n")
                        if option in POSSIBLE_FLAGS_WORD:
                            to_add = long_option
                            current_option = option
                            long_option = ""
                        else:
                            long_option += " " + option
                    elif current_option == "-drop":
                        drop = True
                        if to_add != "":
                            raise RuntimeError(f"special case of {name} already set\n")
                        if option in POSSIBLE_FLAGS_WORD:
                            to_add = long_option
                            current_option = option
                            long_option = ""
                        else:
                            long_option += " " + option
                    else:
                        raise RuntimeError("unknown flag or false flag usage\n")

                if long_option != "":
                    if current_option == "-l":
                        if lang != "Eng":
                            other_names.append((long_option.strip(), lang))
                        else:
                            if to_add != "":
                                raise RuntimeError(
                                    "special case of" + f" {name} already set\n"
                                )
                            to_add = long_option
                        lang = ""
                        long_option = ""
                        current_option = ""
                    elif current_option == "-add":
                        if to_add != "":
                            raise RuntimeError(f"special case of {name} already set\n")
                        to_add = long_option
                        long_option = ""
                        current_option = ""
                    elif current_option == "-drop":
                        drop = True
                        if to_add != "":
                            raise RuntimeError(f"special case of {name} already set\n")
                        to_add = long_option
                        long_option = ""
                        current_option = ""

                if current_option != "":
                    raise RuntimeError(f"{current_option} flag set but not used\n")

                already_in_list = False
                if name in self.definition_list:
                    already_in_list = True
                    if self.definition_list[name].type_ != line_type_list:
                        raise RuntimeError(
                            f"{name} already defined" + " with a different type\n"
                        )
                    self.definition_list[name].other_names += other_names
                if not already_in_list:
                    self.definition_list.update(
                        {
                            name: Definition(
                                name=name,
                                drop=drop,
                                type_=line_type_list,
                                other_names=other_names,
                                to_add=to_add,
                            )
                        }
                    )

    def include_handle(self, line: str) -> Result[str]:
        """
        Überprüft die include Datei um das passende Format zu erkennen
        Der Pfad ist immer in Abhängigkeit von der lex Datei anzugeben.
        """
        line_array = shlex.split(line)
        import_file_name = line_array[1]
        ending = import_file_name.split(".")[-1]
        if ending == import_file_name:  # In this case it is a MMT file with no ending
            ending = ""
        lexicon_dir_path = os.path.dirname(self.lexicon_path)
        import_file_path = os.path.join(lexicon_dir_path, import_file_name)

        # den Import in die Liste hinzufügen
        if ending == "gf":
            # Sprachen hinzufügen
            langs: list[str] = []
            current_option = ""
            for option in line_array[2:]:
                if current_option == "":
                    current_option = option
                elif current_option == "-l":
                    current_option = ""
                    langs.append(option)

            if not langs:
                langs.append("Eng")

            # Überprüfung ob es sich bei der gf Datei um ein resource handelt
            with open(import_file_path, "r", encoding="UTF-8") as import_file:
                file_r = parsing.identify_file(import_file.read())
                if file_r.success:
                    if file_r.value[0] == "gf-resource":
                        for lang in langs:
                            importer = Importer(
                                link=import_file_path,
                                format_=Format.GF_RESOURCE,
                                lang=lang,
                            )
                            self.import_files.append(importer)
                    elif file_r.value[0] == "gf-abstract":
                        importer = Importer(
                            link=import_file_path,
                            format_=Format.GF_ABSTRACT,
                        )
                        self.import_files.append(importer)
                        self.create_cat = False
                    elif file_r.value[0] == "gf-concrete":
                        for lang in langs:
                            importer = Importer(
                                link=import_file_path,
                                format_=Format.GF_CONCRETE,
                                lang=lang,
                            )
                            self.import_files.append(importer)
                    else:
                        return Result(
                            False,
                            None,
                            f"{import_file_name} is not a abstract or resource file\n",
                        )
        elif ending == "":  # MMT Dateien werden ohne Endung Angegeben
            # MMT Dateien werden nicht überprüft. Stattdesen wird mithilfe einer Flag
            # angegeben wohin der import gehen soll.
            if len(line_array) != 3:
                return Result(False, None, f"Wrong argument number: Error in {line}\n")
            if line_array[2] == "-theory":
                importer = Importer(link=import_file_name, format_=Format.MMT_TYPE)
                self.import_files.append(importer)
            elif line_array[2] == "-view":
                importer = Importer(link=import_file_name, format_=Format.MMT_VIEW)
                self.import_files.append(importer)
            else:
                return Result(
                    False, None, f"{line_array[2]} have to be -theory or -view\n"
                )
        else:
            return Result(
                False,
                None,
                f"{import_file_name} is not a gf or a mmt file\n",
            )
        return Result(True, "\n")

    def lang_handle(self, lang: str, name: str) -> Result[None]:
        if name in self.definition_list:
            for _, language in self.definition_list[name].other_names:
                if lang == language:
                    return Result(
                        False,
                        logs=f"{name} already definied" + f" in the language {lang}",
                    )
        if lang not in self.languages:
            self.languages.append(lang)
        return Result(True)

    def create_gf_abstract_cat(self) -> Result[str]:
        """
        Erstellst die Datei GF abstract, die nur den cat Teil beinhaltet,
        mit dem {self.lexicon_name}Cat.gf als Namen
        """
        file_ending = "Cat.gf"
        auto_comm_gf = "-- This is auto-generated. Pls do not modify.\n"
        write_name: str = os.path.join(self.cwd, self.lexicon_name + file_ending)
        if self.file_check(write_name, auto_comm_gf):
            with open(write_name, "w", encoding="UTF-8") as gfabsc:
                gfabsc.write(auto_comm_gf)
                gfabsc.write(f"abstract {self.lexicon_name}Cat = " + "{\n")
                gfabsc.write("flags\n\t coding=utf8 ;\n")

                # die vorhandenen Typen
                gfabsc.write("\tcat\n")
                for type_definition in self.type_def_list:
                    gfabsc.write(f"\t\t{type_definition.name.single_type};\n")

                gfabsc.write("}")
            return Result(True, file_ending)
        return Result(False, None, f"{write_name} already exists")

    def create_gf_abstract_fun(self) -> Result[str]:
        """
        Erstellst die Datei GF abstract mit dem {self.lexicon_name}.gf als Namen
        """
        file_ending = ".gf"
        auto_comm_gf = "-- This is auto-generated. Pls do not modify.\n"
        write_name: str = os.path.join(self.cwd, self.lexicon_name + file_ending)
        if self.file_check(write_name, auto_comm_gf):
            with open(write_name, "w", encoding="UTF-8") as gfabs:
                gfabs.write(auto_comm_gf)
                if self.create_cat:
                    gfabs.write(
                        f"abstract {self.lexicon_name} = "
                        + f"{self.lexicon_name}Cat ** "
                        + "{\n"
                    )
                else:
                    gf_abstract_cats = ""
                    for importer in self.import_files:
                        if importer.format_ == Format.GF_ABSTRACT:
                            import_name = os.path.basename(importer.link[:-3])
                            gf_abstract_cats += import_name + ", "
                    gf_abstract_cats = gf_abstract_cats[:-2]
                    gfabs.write(
                        f"abstract {self.lexicon_name} = "
                        + f"{gf_abstract_cats} ** "
                        + "{\n"
                    )

                gfabs.write("flags\n\t coding=utf8 ;\n")
                gfabs.write("\tfun\n")
                for definition in self.definition_list.values():
                    gfabs.write(f"\t\t{definition.name} : ")
                    final_type: str = ""
                    for typ in definition.type_:
                        final_type += typ.single_type + " -> "
                    final_type = final_type[:-4]
                    gfabs.write(f"{final_type};\n")

                gfabs.write("}")
            return Result(True, file_ending)
        return Result(False, None, f"{write_name} already exists\n")

    def create_gf_concrete(self, language: str) -> Result[str]:
        """
        Erstellt die GF concrete Datei mit {self.lexicon_name}{language}.gf als Namen
        """
        # default englishFile
        file_ending = f"{language}.gf"
        auto_comm_eng = "-- This is auto-generated. Pls do not modify.\n"
        write_name: str = os.path.join(self.cwd, self.lexicon_name + file_ending)
        if self.file_check(write_name, auto_comm_eng):
            with open(write_name, "w", encoding="UTF-8") as gfcon:
                gfcon.write(auto_comm_eng)

                open_needed: bool = False
                extend_needed: bool = False
                for importer in self.import_files:
                    if importer.format_ == Format.GF_RESOURCE:
                        if importer.lang == language:
                            open_needed = True

                    elif importer.format_ == Format.GF_CONCRETE:
                        if importer.lang == language:
                            extend_needed = True

                open_string = ""
                if open_needed:
                    opened_resources = ""
                    for importer in self.import_files:
                        if importer.format_ == Format.GF_RESOURCE:
                            if importer.lang == language:
                                import_name = os.path.basename(importer.link[:-3])
                                opened_resources += import_name + ", "
                    opened_resources = opened_resources[:-2]
                    open_string = f"open {opened_resources} in "

                extend_string = ""
                if extend_needed:
                    extends = ""
                    for importer in self.import_files:
                        if importer.format_ == Format.GF_CONCRETE:
                            if importer.lang == language:
                                import_name = os.path.basename(importer.link[:-3])
                                extends += import_name + ", "
                    extends = extends[:-2]
                    extend_string = f"{extends} ** "

                gfcon.write(
                    f"concrete {self.lexicon_name}{language}"
                    + f" of {self.lexicon_name} = "
                    + extend_string
                    + open_string
                    + "{\n"
                )

                gfcon.write("flags\n\t coding=utf8 ;\n")

                # default Fall: Str
                # Falls concrete importiert wird, wird der lincat Teil übersprungen
                if not extend_needed:
                    gfcon.write("\tlincat\n")
                    for type_definition in self.type_def_list:
                        written: bool = False
                        for form, lang in type_definition.gf_forms:
                            if lang == language:
                                gfcon.write(
                                    f"\t\t{type_definition.name.single_type} ="
                                    + f" {form};\n"
                                )
                                written = True
                                break
                        if not written:  # default
                            gfcon.write(
                                f"\t\t{type_definition.name.single_type} = Str;\n"
                            )

                gfcon.write("\tlin\n")
                for definition in self.definition_list.values():
                    if len(definition.type_) == 1:
                        mk_string = f"mk{definition.type_[0].single_type}"
                        for type_definition in self.type_def_list:
                            if type_definition.name == definition.type_[0]:
                                for constr, lang in type_definition.constructor:
                                    if lang == language:
                                        mk_string = constr
                                        break
                                break
                        # Sprachen und Zusätze
                        input_name = f'"{definition.name}"'
                        if definition.drop:
                            input_name = ""
                        if language == "Eng" and definition.to_add != "":
                            input_name += " " + definition.to_add
                        else:
                            for other_name, lang in definition.other_names:
                                if lang == language:
                                    input_name = other_name
                                    break
                        # nur Wörter der Form "Peter : Name"
                        input_name = input_name.strip()
                        gfcon.write(
                            f"\t\t{definition.name} = " + f"{mk_string} {input_name};\n"
                        )

                gfcon.write("}")
            return Result(True, file_ending)
        return Result(False, None, f"{write_name} already exists\n")

    def create_mmt_semantics(self) -> Result[str]:
        """
        Erstellt die MMT Datei mit den Semantics, die später im view verwendet wird.
        """
        file_ending = "Semantics.mmt"
        auto_comm_sem = "// This is auto-generated. Pls do not modify.❚\n"
        write_name: str = os.path.join(self.cwd, self.lexicon_name + file_ending)
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
                        mmtsem.write(f"\tinclude {importer.link} ❙\n")

                for definition in self.definition_list.values():
                    mmt_definition_type: str = ""
                    for type_definition in self.type_def_list:
                        if type_definition.name == definition.type_[0]:
                            mmt_definition_type = type_definition.mmt_form
                    if mmt_definition_type == "":
                        return (False, None, f"{definition.type_[0]} is not definied in the lexicon")
                    mmtsem.write(f"\t{definition.name} : {mmt_definition_type} ❙\n")
                mmtsem.write("❚")
            return Result(True, file_ending)
        return Result(False, None, f"{write_name} already exists")

    def create_mmt_sem_constr(self) -> Result[str]:
        """
        Erstellt die MMT Datei, die den view von der erstellten GF abstract
        zur MMT Semantics beinhaltet.
        """
        file_ending = "SemConstr.mmt"
        auto_comm_semcon = "// This is auto-generated. Pls do not modify.❚\n"
        write_name: str = os.path.join(self.cwd, self.lexicon_name + file_ending)
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
                        mmtsemcon.write(f"\tinclude {importer.link} ❙\n")

                # Falls ein abstract gf cat gegeben wird, dürfen die Type Defs
                # nicht nochmal in den view, da dies dann gegeben sein müssen
                if self.create_cat:
                    for type_definition in self.type_def_list:
                        mmtsemcon.write(
                            f"\t{type_definition.name.single_type} ="
                            + f" {type_definition.mmt_form} ❙\n"
                        )

                for definition in self.definition_list.values():
                    if len(definition.type_) == 1:
                        mmtsemcon.write(f"\t{definition.name} = {definition.name} ❙\n")

                mmtsemcon.write("❚")
            return Result(True, file_ending)
        return Result(False, None, f"{write_name} already exists\n")

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
                return False
        return True

    def get_lexicon_name(self) -> str:
        return self.lexicon_name

    def create_gf(self) -> Result[list[str]]:
        logs: list[str] = []
        success: bool = True
        file_names: list[str] = []

        if self.create_cat:  # Nur erstellen wenn kein gf abstract cat gegeben wird.
            result = self.create_gf_abstract_cat()
            if result.success:
                file_names.append(result.value)
            else:
                logs.append(result.logs)
                success = False

        result = self.create_gf_abstract_fun()
        if result.success:
            file_names.append(result.value)
        else:
            logs.append(result.logs)
            success = False

        for lang in self.languages:
            result = self.create_gf_concrete(lang)
            if result.success:
                file_names.append(result.value)
            else:
                logs.append(result.logs)
                success = False

        if success:
            return Result(True, file_names, "\n".join(logs))
        return Result(False, file_names, "\n".join(logs))

    def create_mmt(self) -> Result[list[str]]:
        logs: list[str] = []
        success: bool = True
        file_names: list[str] = []

        result = self.create_mmt_semantics()
        if result.success:
            file_names.append(result.value)
        else:
            logs.append(result.logs)
            success = False

        result = self.create_mmt_sem_constr()
        if result.success:
            file_names.append(result.value)
        else:
            logs.append(result.logs)
            success = False

        if success:
            return Result(True, file_names, "\n".join(logs))
        return Result(False, file_names, "\n".join(logs))

    def create_all(self) -> Result[list[str]]:
        logs: list[str] = []
        success: bool = True
        file_names: list[str] = []

        result = self.create_gf()
        file_names += result.value
        logs.append(result.logs)
        if not result.success:
            success = False

        result = self.create_mmt()
        file_names += result.value
        logs.append(result.logs)
        if not result.success:
            success = False

        if success:
            return Result(True, file_names, "\n".join(logs))
        return Result(False, file_names, "\n".join(logs))
