# import re


# def split_tables(markdown):

#     tables = re.findall(
#         r"\[TABLE_BLOCK\](.*?)\[/TABLE_BLOCK\]",
#         markdown,
#         flags=re.DOTALL
#     )


#     result=[]


#     for table in tables:

#         table = table.strip()

#         if not table.strip():
#             continue


#         result.append(
#             "[TABLE_BLOCK]\n"
#             + table
#             + "\n[/TABLE_BLOCK]"
#         )


#     return result
import re


def split_tables(markdown):

    pattern = re.compile(
        r"\[TABLE_BLOCK\](.*?)\[TABLE_BLOCK\]",
        flags=re.DOTALL
    )


    tables = []


    matches = pattern.findall(markdown)


    for m in matches:

        tables.append(
            "[TABLE_BLOCK]\n" + m.strip()
        )


    return tables