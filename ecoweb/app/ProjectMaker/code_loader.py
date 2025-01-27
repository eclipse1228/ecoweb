import os
from typing import List, Dict
import re
import copy
import itertools

# 서드 파티 패턴 정의
THIRD_PARTY_PATTERNS = {
    "classes": [r'^slick-.*$', r'^slide-.*$', r'^React.*$', r'^use.*$', r'^v-.*$', r'^materialize-.*$', r'^foundation-.*$', r'^swiper-.*$', r'^col-', r'^(sm|md|lg|xl):.*$', r'^lg:', r'^fa-.*$'],
    "ids": [],
    "functions": [r'^jQuery'],
    "variables": [],
}

def generate_replace_strings():
    """
    Generate a sequence of replacement strings in order: 1-byte, 2-byte, 3-byte, ...
    """
    chars = "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ"
    # 1-byte replacements
    for char in chars:
        yield char
    # Multi-byte replacements
    for size in range(2, 6):  # Arbitrary limit; can expand as needed
        for combo in itertools.product(chars, repeat=size):
            yield "".join(combo)

def assign_replacement(data):
    """
    Assign replacement strings to the data list based on the sorting criteria.
    :param data: List of dictionaries containing 'name', 'account', and other keys.
    :return: Modified data with 'replace' field populated.
    """
    # Calculate the sort key: total bytes (name length * account) and account for ties
    for item in data:
        item['total_bytes'] = len(item['name']) * item['account']

    # Sort the data: prioritize by total_bytes descending, account ascending for ties
    sorted_data = sorted(data, key=lambda x: (-x['total_bytes'], x['account']))

    # Generate replacement strings and assign to each item
    replacement_generator = generate_replace_strings()
    for item in sorted_data:
        item['replace'] = next(replacement_generator)

    # Cleanup: remove 'total_bytes' (used only for sorting)
    for item in data:
        del item['total_bytes']

    # Update the "replace_pattern" field
    for item in sorted_data:
        item['replace_pattern'] = [
            pattern.replace(item['name'], item['replace']) for pattern in item['pattern']
        ]

    return data

def filter_tuple(tuple_list):
    result = []
    for input_tuple in tuple_list:
        # 빈 문자열 제거
        filtered_tuple = tuple(filter(bool, input_tuple))

        # 남아있는 문자열 하나를 추출
        if len(filtered_tuple) == 1:
            result.append(filtered_tuple[0])
    return result

def patternNameMerge(pattern, name):
    ret = []
    for i in range(len(pattern)):
        new_item = {
            "name" : name[i],
            "pattern" : pattern[i]
        }
        ret.append(new_item)
    return ret

def elementsUpdate(elements, item_list, item):
    for match in item_list:
        isThirdParty = False
        for iter in THIRD_PARTY_PATTERNS[item]:
            if re.fullmatch(iter, match["name"]):
                isThirdParty = True
                break
        if isThirdParty: continue
        if len(match["name"]) > 2:  # 길이가 2바이트 초과인 경우에만 추가
            existing_item = next((item for item in elements[item] if item["name"] == match["name"]), None)
            if existing_item:
                existing_pattern = next(
                    (pattern for pattern in existing_item["pattern"] if pattern == match["pattern"]), None)
                existing_item["account"] += 1
                if not existing_pattern:
                    existing_item["pattern"].append(match["pattern"])
            else:
                new_item = {
                    "pattern": [],
                    "name": match["name"],
                    "account": 1,
                    "replace": "",
                    "replace_pattern": []
                }
                new_item["pattern"].append(match["pattern"])
                elements[item].append(new_item)
    return elements

def find_with_pattern_labels(pattern: str, text: str) -> List[str]:
    """
    주어진 정규 표현식 패턴과 문자열에서 매치된 텍스트를 원본 문자열 형식 그대로 반환하는 함수.

    Args:
    - pattern (str): 정규표현식 패턴.
    - text (str): 검색할 문자열.

    Returns:
    - List[str]: 매치된 텍스트가 원본 형식 그대로 담긴 리스트.
    """
    matches = []
    for match in re.finditer(pattern, text):
        # 일치한 부분의 시작과 끝 위치를 통해 원본 텍스트에서 해당 부분을 추출
        start, end = match.span()
        matches.append(text[start:end])

    return matches

def collect_project_files(root_path: str) -> List[str]:
    """
    프로젝트 폴더를 순회하여 .html, .css, .js 파일의 절대 경로를 수집하는 함수.

    Args:
    - root_path (str): 프로젝트의 루트 경로.

    Returns:
    - List[str]: HTML, CSS, JS 파일들의 절대 경로 리스트.
    """
    collected_files = []
    for dirpath, _, filenames in os.walk(root_path):
        for filename in filenames:
            # 파일 확장자가 html, css, js인지 확인
            if filename.endswith(('.html', '.css', '.js', '.do')):
                # 파일의 절대 경로를 생성하여 리스트에 추가
                absolute_path = os.path.join(dirpath, filename)
                collected_files.append(os.path.abspath(absolute_path))
    return collected_files

# HTML 파일 로드
def load_html_content(file_path: str) -> str:
    with open(file_path, 'r', encoding='utf-8') as file:
        html_content = file.read()
    return html_content
# CSS 파일 로드
def load_css_content(file_path: str) -> str:
    with open(file_path, 'r', encoding='utf-8') as file:
        css_content = file.read()

    return css_content
# JS 파일 로드
def load_js_content(file_path: str) -> str:
    with open(file_path, 'r', encoding='utf-8') as file:
        js_content = file.read()
    return js_content

def html_analize(html_code: str, elements):
    """
    HTML 코드 문자열에서 <style>, <body>, <script> 태그 내의 id와 class 이름을 추출하여,
    각 요소와 발견 횟수를 알아냅니다. 또한 <script> 태그 내에서 정의된 변수명과 함수명을 추출하여,
    각 요소와 발견 횟수를 알아냅니다. <body> 태그 내에서는 인라인 방식으로 사용된 함수명을 추가로 식별합니다.

    Args:
    - html_code (str): HTML 코드 문자열

    Returns:
    - List[dict]: 각 요소의 이름과 발견 횟수를 저장한 리스트.
    """


    # <style> 태그 내의 내용에서 id와 class 추출
    style_content = re.findall(r'<style.*?>(.*?)</style>', html_code, re.DOTALL)
    for style in style_content:
        # id 추출
        id_matches = re.findall(r'#(?![0-9a-fA-F]{3}(?:[0-9a-fA-F]{1,5})?\b)([a-zA-Z0-9_-]+)', style)
        id_pattern_matches = find_with_pattern_labels(r'#(?![0-9a-fA-F]{3}(?:[0-9a-fA-F]{1,5})?\b)([a-zA-Z0-9_-]+)', style)
        # class 추출 (앞에 공백이나 줄바꿈이 있는 경우만)
        class_matches = re.findall(r'(?<=\s|\n)\.([a-zA-Z0-9_-]+)', style)
        class_pattern_matches = find_with_pattern_labels(r'(?<=\s|\n)\.([a-zA-Z0-9_-]+)', style)

        # name과 pattern을 합치기
        id_list = patternNameMerge(name=id_matches, pattern=id_pattern_matches)
        elements = elementsUpdate(elements=elements, item_list=id_list, item="ids")
        class_list = patternNameMerge(name=class_matches, pattern=class_pattern_matches)
        elements = elementsUpdate(elements=elements, item_list=class_list, item="classes")

    # <script> 태그 내의 내용에서 변수명, 함수명, id, class 추출
    script_content = re.findall(r'<script.*?>(.*?)</script>', html_code, re.DOTALL)
    for script in script_content:
        # 변수명 추출 (var, let, const 뒤에 오는 변수 이름)
        variable_matches = re.findall(r'\b(?:var|let|const)\s+([a-zA-Z_$][a-zA-Z0-9_$]*)', script)
        variable_pattern_matches = find_with_pattern_labels(r'\b(?:var|let|const)\s+([a-zA-Z_$][a-zA-Z0-9_$]*)', script)
        # 함수명 추출 (함수 선언, 함수 표현식, 화살표 함수)
        function_matches = re.findall(
            r'\bfunction\s+([a-zA-Z_$][a-zA-Z0-9_$]*)|'  # 함수 선언
            r'([a-zA-Z_$][a-zA-Z0-9_$]*)\s*=\s*function\b|'  # 함수 표현식
            r'([a-zA-Z_$][a-zA-Z0-9_$]*)\s*=\s*\(.*?\)\s*=>'  # 화살표 함수
            , script
        )
        function_matches = filter_tuple(function_matches)
        function_pattern_matches = find_with_pattern_labels(
            r'\bfunction\s+([a-zA-Z_$][a-zA-Z0-9_$]*)|'  # 함수 선언
            r'([a-zA-Z_$][a-zA-Z0-9_$]*)\s*=\s*function\b|'  # 함수 표현식
            r'([a-zA-Z_$][a-zA-Z0-9_$]*)\s*=\s*\(.*?\)\s*=>'  # 화살표 함수
            , script
        )

        variables_list = patternNameMerge(name=variable_matches, pattern=variable_pattern_matches)
        elements = elementsUpdate(elements=elements, item_list=variables_list, item="variables")
        functions_list = patternNameMerge(name=function_matches, pattern=function_pattern_matches)
        elements = elementsUpdate(elements=elements, item_list=functions_list, item="functions")

        # id와 class 추출
        script_id_matches = re.findall(r'\bgetElementById\(["\']([a-zA-Z0-9_-]+)["\']\)', script)
        script_id_pattern_matches = find_with_pattern_labels(r'\bgetElementById\(["\']([a-zA-Z0-9_-]+)["\']\)', script)
        script_id_list = patternNameMerge(name=script_id_matches, pattern=script_id_pattern_matches)
        elements = elementsUpdate(elements=elements, item_list=script_id_list, item="ids")

        script_class_matches = re.findall(r'\bgetElementsByClassName\(["\']([a-zA-Z0-9_\s-]+)["\']\)', script)
        script_class_pattern_matches = find_with_pattern_labels(r'\bgetElementsByClassName\(["\']([a-zA-Z0-9_\s-]+)["\']\)', script)
        script_class_list = patternNameMerge(name=script_class_matches, pattern=script_class_pattern_matches)
        elements = elementsUpdate(elements=elements, item_list=script_class_list, item="classes")

        id_pattern1 = r'[\'\"\s]#([a-zA-Z_][\w\-]*)'
        class_pattern2 = r'[\'\"\s]\.([a-zA-Z0-9_-]+)'
        # 정규 표현식을 사용하여 모든 매칭되는 패턴을 추출합니다.
        id_matches = re.findall(id_pattern1, script)
        id_pattern_matches = find_with_pattern_labels(id_pattern1, script)
        id_list = patternNameMerge(pattern=id_pattern_matches, name=id_matches)
        elements=elementsUpdate(elements=elements, item_list=id_list, item="ids")

        class_matches = re.findall(class_pattern2, script)
        class_pattern_matches = find_with_pattern_labels(class_pattern2, script)
        class_list = patternNameMerge(pattern=class_pattern_matches, name=class_matches)
        elements=elementsUpdate(elements=elements, item_list=class_list, item="classes")

    # <body> 태그 내의 내용에서 id와 class, 인라인 이벤트 및 href 속성에서 함수명 추출
    body_content = re.search(r'<body.*?>(.*?)</body>', html_code, re.DOTALL)
    if body_content:
        body_content = body_content.group(1)

        # id와 class 속성 추출
        id_matches = re.findall(r'\bid=["\']([a-zA-Z0-9_-]+)["\']', body_content)
        id_pattern_matches = find_with_pattern_labels(pattern=r'\bid=["\']([a-zA-Z0-9_-]+)["\']', text=body_content)
        id_list = patternNameMerge(pattern=id_pattern_matches, name=id_matches)
        elements=elementsUpdate(elements=elements, item_list=id_list, item="ids")

        class_matches = re.findall(r'(class=\"[^"]+\")', body_content)
        for classLine in class_matches:
            classname_matches = (
                re.findall(r'\"([a-zA-Z0-9_-]+)', classLine) +
                re.findall(r'\s([a-zA-Z0-9_-]+)\s', classLine) +
                re.findall(r'\s([a-zA-Z0-9_-]+)\"', classLine)
            )
            classname_pattern_matches = (
                find_with_pattern_labels(r'\"([a-zA-Z0-9_-]+)', classLine) +
                find_with_pattern_labels(r'\s([a-zA-Z0-9_-]+)\s', classLine) +
                find_with_pattern_labels(r'\s([a-zA-Z0-9_-]+)\"', classLine)
            )
            classname_list = patternNameMerge(pattern=classname_pattern_matches, name=classname_matches)
            elements = elementsUpdate(elements=elements, item_list=classname_list, item="classes")



        # 인라인 이벤트 속성에서 함수명 추출 (예: onclick="functionName(...)")
        event_function_matches = re.findall(r'\bon\w+="([a-zA-Z_$][a-zA-Z0-9_$]*)\(', body_content)
        event_function_pattern_matches = find_with_pattern_labels(r'\bon\w+="([a-zA-Z_$][a-zA-Z0-9_$]*)\(', body_content)
        event_function_list = patternNameMerge(pattern=event_function_pattern_matches, name=event_function_matches)
        elements=elementsUpdate(elements=elements, item_list=event_function_list, item="functions")

        # href="javascript:" 구문에서 함수명 추출 (예: href="javascript:functionName(...)")
        href_function_matches = re.findall(r'href=["\']javascript:([a-zA-Z_$][a-zA-Z0-9_$]*)\(', body_content)
        href_function_pattern_matches = find_with_pattern_labels(r'href=["\']javascript:([a-zA-Z_$][a-zA-Z0-9_$]*)\(', body_content)
        href_list = patternNameMerge(pattern=href_function_pattern_matches, name=href_function_matches)
        elements = elementsUpdate(elements=elements, item_list=href_list, item="functions")

    return elements

def css_analize(css_code, elements):
    id_matches = re.findall(r'#(?![0-9a-fA-F]{3}(?:[0-9a-fA-F]{1,5})?\b)([a-zA-Z0-9_-]+)', css_code)
    id_pattern_matches = find_with_pattern_labels(r'#(?![0-9a-fA-F]{3}(?:[0-9a-fA-F]{1,5})?\b)([a-zA-Z0-9_-]+)', css_code)
    id_list = patternNameMerge(pattern=id_pattern_matches, name=id_matches)
    elements= elementsUpdate(elements=elements, item_list=id_list, item="ids")

    class_matches = re.findall(r"\.([\w-]+)(?=[,\s{:])", css_code)
    class_pattern_matches = find_with_pattern_labels(r"\.([\w-]+)(?=[,\s{:])", css_code)
    class_list = patternNameMerge(pattern=class_pattern_matches, name=class_matches)
    elements = elementsUpdate(elements=elements, item_list=class_list, item="classes")

    return elements

def js_analize(js_code, elements : dict):
    css_elements = (
        re.findall(r"\"#([\w-]+)", js_code) +
        re.findall(r"[\"\'\s]\.([a-zA-Z0-9_-]+)", js_code)
    )
    css_elements_pattern = (
            find_with_pattern_labels(r"\"#([\w-]+)", js_code) +
            find_with_pattern_labels(r"[\"\'\s]\.([a-zA-Z0-9_-]+)", js_code)
    )
    css_list = patternNameMerge(pattern=css_elements_pattern, name=css_elements)
    for ele in css_list:
        isId = False
        for id in elements["ids"]:
            if id["name"] == ele["name"]:
                id["account"] += 1
                if ele["pattern"] not in id["pattern"]:
                    id["pattern"].append(ele["pattern"])
                isId = True
                break
        if not isId:
            for c in elements["classes"]:
                if c["name"] == ele["name"]:
                    c["account"] += 1
                    if ele["pattern"] not in c["pattern"]:
                        c["pattern"].append(ele["pattern"])
                    break
    val_matches = re.findall(r"/\b(?:var|let|const)\s+([a-zA-Z_$][\w$]*)(?=\s*[=;])/g", js_code)
    val_pattern_matches = find_with_pattern_labels(r"/\b(?:var|let|const)\s+([a-zA-Z_$][\w$]*)(?=\s*[=;])/g", js_code)
    val_list = patternNameMerge(pattern=val_pattern_matches, name=val_matches)
    elements = elementsUpdate(elements=elements, item_list=val_list, item="variables")

    function_matches = re.findall(
        r'\bfunction\s+([a-zA-Z_$][a-zA-Z0-9_$]*)|'  # 함수 선언
        r'([a-zA-Z_$][a-zA-Z0-9_$]*)\s*=\s*function\b|'  # 함수 표현식
        r'([a-zA-Z_$][a-zA-Z0-9_$]*)\s*=\s*\(.*?\)\s*=>'  # 화살표 함수
        , js_code
    )
    function_matches = filter_tuple(function_matches)
    function_pattern_matches = find_with_pattern_labels(
        r'\bfunction\s+([a-zA-Z_$][a-zA-Z0-9_$]*)|'  # 함수 선언
        r'([a-zA-Z_$][a-zA-Z0-9_$]*)\s*=\s*function\b|'  # 함수 표현식
        r'([a-zA-Z_$][a-zA-Z0-9_$]*)\s*=\s*\(.*?\)\s*=>'  # 화살표 함수
        , js_code
    )
    function_list = patternNameMerge(pattern=function_pattern_matches, name=function_matches)
    elements = elementsUpdate(elements=elements, item_list= function_list, item="functions")

    val_use_matches = re.findall(r"/\b([a-zA-Z_$][\w$]*)\b(?=\s*[+*/%-=;\)\],]|\s*,|\s*\)|\s*\[|\.|\$\{|[:,=}\]])/g", js_code)
    val_use_pattern_matches = find_with_pattern_labels(r"/\b([a-zA-Z_$][\w$]*)\b(?=\s*[+*/%-=;\)\],]|\s*,|\s*\)|\s*\[|\.|\$\{|[:,=}\]])/g", js_code)
    val_use_list = patternNameMerge(pattern=val_use_pattern_matches, name=val_use_matches)
    elements = elementsUpdate(elements=elements, item_list= val_use_list, item="variables")

    func_use_matches = re.findall(r"/\b([a-zA-Z_$][\w$]*)(?=\s*[),]|\()/g", js_code)
    func_use_pattern_matches = find_with_pattern_labels(r"/\b([a-zA-Z_$][\w$]*)(?=\s*[),]|\()/g", js_code)
    func_use_list = patternNameMerge(pattern=func_use_pattern_matches, name=func_use_matches)
    elements = elementsUpdate(elements=elements, item_list= func_use_list, item="functions")

    return elements


def load_code_objects(file_path: str, elements):
    if file_path.endswith(('.html', '.do')):
        content = load_html_content(file_path)
        return html_analize(html_code=content, elements=elements)
    elif file_path.endswith('.css'):
        content = load_css_content(file_path)
        return css_analize(css_code=content, elements=elements)
    elif file_path.endswith('.js'):
        content = load_js_content(file_path)
        return js_analize(js_code=content, elements=elements)
    return "error"

def compare_elements(elements1, elements2):
    # Initialize the result dictionary
    result = {
        "ids": [],
        "classes": [],
        "variables": [],
        "functions": []
    }

    def compare_lists(list1, list2, key):
        # Convert lists to dictionaries indexed by 'name'
        dict1 = {item['name']: item for item in list1}
        dict2 = {item['name']: item for item in list2}

        # Find keys that exist in both dictionaries
        common_keys = set(dict1.keys()).intersection(set(dict2.keys()))
        # Find keys that exist in only one dictionary
        unique_keys_1 = set(dict1.keys()) - set(dict2.keys())
        unique_keys_2 = set(dict2.keys()) - set(dict1.keys())

        # Compare elements with the same name
        for name in common_keys:
            item1 = dict1[name]
            item2 = dict2[name]
            if item1["pattern"] != item2["pattern"] or item1["account"] != item2["account"]:
                result[key].append({
                    "name": name,
                    "pattern1": item1["pattern"],
                    "pattern2": item2["pattern"],
                    "account1": item1["account"],
                    "account2": item2["account"],
                    "replace1": item1["replace"],
                    "replace2": item2["replace"],
                    "replace_pattern1": item1["replace_pattern"],
                    "replace_pattern2": item2["replace_pattern"],
                })

        # Add unique elements from list1
        for name in unique_keys_1:
            result[key].append({
                "name": name,
                "pattern1": dict1[name]["pattern"],
                "pattern2": None,
                "account1": dict1[name]["account"],
                "account2": 0,
                "replace1": dict1[name]["replace"],
                "replace2": None,
                "replace_pattern1": dict1[name]["replace_pattern"],
                "replace_pattern2": None,
            })

        # Add unique elements from list2
        for name in unique_keys_2:
            result[key].append({
                "name": name,
                "pattern1": None,
                "pattern2": dict2[name]["pattern"],
                "account1": 0,
                "account2": dict2[name]["account"],
                "replace1": None,
                "replace2": dict2[name]["replace"],
                "replace_pattern1": None,
                "replace_pattern2": dict2[name]["replace_pattern"],
            })

    # Compare each category in the elements
    compare_lists(elements1["ids"], elements2["ids"], "ids")
    compare_lists(elements1["classes"], elements2["classes"], "classes")
    compare_lists(elements1["variables"], elements2["variables"], "variables")
    compare_lists(elements1["functions"], elements2["functions"], "functions")

    return result

def thirdParty_ClassDetect(elements):
    # 리스트 복사본을 사용하여 안전하게 순회
    classes_to_remove = []

    for cls in elements["classes"]:
        isThirdParty = False
        for pattern in THIRD_PARTY_PATTERNS["class"]:
            if re.search(pattern, cls["name"]):
                # 현재 클래스가 서드 파티 패턴과 일치하면 삭제 대상에 추가
                isThirdParty = True
                break

        if isThirdParty:
            classes_to_remove.append(cls)

    # 삭제 대상 클래스 제거
    for cls in classes_to_remove:
        elements["classes"].remove(cls)

    return elements

def code_optimizer(root_path):
    elements = {
        "ids": [],
        "classes": [],
        "variables": [],
        "functions": []
    }
    path_list = collect_project_files(root_path)

    for path in path_list:
        elements = load_code_objects(path, elements)

    elements["ids"] = assign_replacement(elements["ids"])
    elements["classes"] = assign_replacement(elements["classes"])

    # for path in path_list:


def code_loader(root_path):
    elements = {
        "ids": [],
        "classes": [],
        "variables": [],
        "functions": []
    }
    path_list = collect_project_files(root_path)

    for path in path_list:
        elements = load_code_objects(path, elements)

    return elements

if __name__ == "__main__":
    """
    elements = 프로젝트 내 모든 파일을 순회하면서 식별한 id, class, 변수명, 함수명을 기록하는 객체
    {
        ids : [
        {
            pattern : 식별된 패턴이 그대로 존재하는 문자열 리스트 (ex: ['id="idName1"', '#idName1']),
            name : 식별된 패턴이 제외된 요소의 이름 (ex: 'idName1'),
            account : 프로젝트 내에서 해당 요소가 사용된 횟수 -> 숫자,
            replace : name에 대응되는 대체 문자열 (ex : 'aab'),
            replace_pattern : 식별된 패턴이 포함된 대체 문자열 (ex : 'id="aab"')
        }, ...
        ],
        classes : [
        {
            pattern : 식별된 패턴이 그대로 존재하는 문자열 리스트,
            name : 식별된 패턴이 제외된 요소의 이름,
            account : 프로젝트 내에서 해당 요소가 사용된 횟수 -> 숫자,
            replace : name에 대응되는 대체 문자열 ,
            replace_pattern : 식별된 패턴이 포함된 대체 문자열
        }, ...
        ],
        variables : [
        {
            pattern : 식별된 패턴이 그대로 존재하는 문자열 리스트,
            name : 식별된 패턴이 제외된 요소의 이름 ,
            account : 프로젝트 내에서 해당 요소가 사용된 횟수 -> 숫자,
            replace : name에 대응되는 대체 문자열 ,
            replace_pattern : 식별된 패턴이 포함된 대체 문자열 
        }, ...],
        functions : [
        {
            pattern : 식별된 패턴이 그대로 존재하는 문자열 리스트,
            name : 식별된 패턴이 제외된 요소의 이름 ,
            account : 프로젝트 내에서 해당 요소가 사용된 횟수 -> 숫자,
            replace : name에 대응되는 대체 문자열 ,
            replace_pattern : 식별된 패턴이 포함된 대체 문자열 
        }, ...]
    }
    """
    elements = {
        "ids": [],
        "classes": [],
        "variables": [],
        "functions": []
    }



