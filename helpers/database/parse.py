import sqlite3

from helpers.file import config


def get_table_names(schema_file):
    """Parse the schema file and return a list of table names."""
    return list(get_table_locations(schema_file).keys())


def get_table_locations(schema_file):
    """Parse the schema file and return a dictionary of table names with their locations [start, end]."""
    current_table = None
    tables = dict()

    with open(schema_file, "r") as f:
        for index, line in enumerate(f.readlines()):
            if line.lower().startswith("create table"):
                current_table = line.split(" ")[5 if 'if not exists' in line.lower() else 2]
                tables[current_table] = [index, None]
            elif ');' in line.lower():
                tables[current_table][1] = index
    return tables


def get_table_variables(schema_file, table_name):
    """Parse the schema file and return the schema for a given table."""
    table_location = get_table_locations(schema_file).get(table_name)
    if table_location is None:
        return None

    variables = dict()
    with open(schema_file, "r") as f:
        for variable in f.read().split("\n")[table_location[0] + 1:table_location[1]]:
            variable = variable.strip()
            if variable.endswith(","):
                variable = variable[:-1]
            split = variable.split(" ")
            variables[split[0]] = split[-1]
    return variables


def table_changes_to_match_schema():
    with sqlite3.connect(config.get('DATABASE_FILE')) as con:
        cur = con.cursor()

        modifications = dict()
        for table in get_table_names(".schema"):
            cur.execute(f"PRAGMA table_info({table})")
            tbl_data = {col[1]: col[2] for col in cur.fetchall()}

            modify = dict()

            for column_name, column_type in get_table_variables(".schema", table).items():
                tbl_type = tbl_data.get(column_name)
                if tbl_type is not None:
                    if tbl_type.lower() != column_type.lower():
                        modify[column_name] = f"MISMATCH {tbl_type} {column_type}"
                else:
                    modify[column_name] = f"ADD {column_name} {column_type}"

            if len(modify) > 0:
                modifications[table] = modify
        return modifications


def get_sql_modifications(modifications: dict):
    modify_sql = []

    for table, columns in modifications.items():
        for column, action in columns.items():
            if action.startswith("MISMATCH"):
                continue
            modify_sql.append(f"ALTER TABLE {table} {action};")

    return "\n".join(modify_sql)
