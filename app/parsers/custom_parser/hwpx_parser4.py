import zipfile
from lxml import etree

def parse_hwpx(path):

    with zipfile.ZipFile(path) as z:
        xml = z.read(
            "Contents/section0.xml"
        )

    root = etree.fromstring(xml)

    ns = {
        "hp":
        "http://www.hancom.co.kr/hwpml/2011/paragraph"
    }


    result=[]


    for table in root.xpath(".//hp:tbl", namespaces=ns):

        rows=[]

        for tr in table.xpath("./hp:tr", namespaces=ns):

            row=[]

            for tc in tr.xpath("./hp:tc", namespaces=ns):

                texts = tc.xpath(
                    ".//hp:t/text()",
                    namespaces=ns
                )

                row.append(
                    "".join(texts)
                )

            rows.append(row)


        result.append(
            {
                "type":"table",
                "content":rows
            }
        )


    return result
# def parse_hwpx(path):

#     with zipfile.ZipFile(path) as z:

#         xml = z.read(
#             "Contents/section0.xml"
#         )

#     root = etree.fromstring(xml)

#     ns = {
#         "hp":
#         "http://www.hancom.co.kr/hwpml/2011/paragraph"
#     }


#     tables=[]

#     for table in root.xpath(".//hp:tbl", namespaces=ns):

#         rows=[]

#         for tr in table.xpath("./hp:tr", namespaces=ns):

#             row=[]

#             for tc in tr.xpath("./hp:tc", namespaces=ns):

#                 texts = tc.xpath(
#                     ".//hp:t/text()",
#                     namespaces=ns
#                 )

#                 row.append(
#                     "".join(texts)
#                 )

#             rows.append(row)

#         tables.append(rows)


#     return tables