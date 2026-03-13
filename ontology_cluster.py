import os
import re
import json
from pathlib import Path
from collections import defaultdict
from tqdm import tqdm

# =====================================================================
# 설정 (Configuration)
# =====================================================================
TARGET_DIR = r"e:\python\유용한 글들"
DOCS_DIR = os.path.join(TARGET_DIR, "Documents")
OUTPUT_HTML = os.path.join(TARGET_DIR, "ontology_visual_map.html")
OUTPUT_MD = os.path.join(TARGET_DIR, "ontology_map_tags.md")

# =====================================================================
# 메인 로직
# =====================================================================
def extract_tags_and_content(file_path):
    """
    파일에서 태그, 요약(첫 100자), 그리고 원문 전체 내용(Full Content)을 추출합니다.
    """
    tags = []
    summary_text = ""
    full_content = ""
    
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            lines = f.readlines()
            
            # 1. 원문 전체 내용 저장
            full_content = "".join(lines)
            
            # 2. 태그 파싱 (문서 전체에서 #태그 패턴 탐색)
            # (?<!#)는 앞에 #이 오지 않아야 함을 의미하여 헤더(###)와 태그(#태그)를 구분합니다.
            matches = re.findall(r'(?<!#)#([^\s#]+)', full_content)
            if matches:
                # 한 문서 내 중복 발견 태그는 제거 후 병합
                tags.extend(list(set(matches)))
            
            # 3. 요약 텍스트 추출 (뷰어 툴팁용)
            clean_content = re.sub(r'#+\s', '', full_content)
            clean_content = re.sub(r'[\*\_\-\`]', ' ', clean_content)
            clean_content = re.sub(r'\[.*?\]\(.*?\)', ' ', clean_content)
            clean_content = re.sub(r'\s+', ' ', clean_content).strip()
            
            main_text_start = clean_content.find("원본:")
            if main_text_start != -1:
                clean_content = clean_content[main_text_start+20:]
            
            summary_text = clean_content[:150].replace('\n', ' ').replace('"', "'") + "..."
            
    except Exception as e:
        print(f"Error reading {file_path.name}: {e}")
        
    return tags, summary_text, full_content

def group_files_by_tags(directory_path):
    """태그를 바탕으로 마크다운 파일을 그룹핑합니다."""
    tag_index = defaultdict(list)
    untagged_files = []
    
    path = Path(directory_path)
    md_files = list(path.glob('*.md'))
    
    print(f"[{directory_path}] 에서 태그 데이터 및 전체 원문 추출 중...")
    
    for file_path in tqdm(md_files, desc="문서 분석 중"):
        file_name = file_path.name
        tags, summary, full_content = extract_tags_and_content(file_path)
        
        file_info = {
            "name": file_name,
            "summary": summary,
            "full_content": full_content
        }
        
        if tags:
            for tag in tags:
                tag_index[tag].append(file_info)
        else:
            untagged_files.append(file_info)
            
    return tag_index, untagged_files

def auto_tag_untagged_files(tag_index, untagged_files):
    """
    태그가 없는 문서들의 본문 내용을 분석하여,
    1단계: 기존 태그 목록 중 본문에 등장하는 키워드와 매칭되는 태그를 자동으로 부여합니다.
    2단계: 그래도 매칭이 안 되면, 본문의 핵심 키워드를 추출하여 새 태그를 만듭니다.
    """
    existing_tags = list(tag_index.keys())
    still_untagged = []
    auto_tagged_count = 0
    new_tag_count = 0
    
    # 한국어 불용어 (조사, 접속사, 일반적인 단어 등)
    stop_words = {
        '그리고', '하지만', '그러나', '또한', '때문에', '위해', '통해', '대한', '관한',
        '이것', '저것', '그것', '이런', '저런', '그런', '어떤', '무엇', '여기', '거기',
        '있다', '있는', '없는', '없다', '하는', '되는', '했다', '된다', '한다', '않는',
        '것이', '수있', '있습', '니다', '입니', '합니', '습니', '하게', '에서', '으로',
        '같은', '이상', '이하', '이전', '이후', '가장', '매우', '아주', '정말', '진짜',
        '우리', '나의', '저의', '그의', '것을', '사람', '하나', '모든', '다른', '가지',
        '만약', '경우', '추가', '사용', '방법', '시작', '결과', '과정', '부분', '문제',
        '작성', '작성자', '원본', '태그', '참고', '출처', '링크', '참조', '관련',
        'the', 'and', 'for', 'that', 'this', 'with', 'you', 'are', 'not', 'but',
        'from', 'have', 'has', 'was', 'were', 'been', 'will', 'can', 'would',
    }
    
    for file_info in untagged_files:
        content_lower = file_info["full_content"].lower()
        matched_tags = []
        
        # --- 1단계: 기존 태그와 매칭 시도 ---
        for tag in existing_tags:
            if tag.lower() in content_lower:
                matched_tags.append(tag)
        
        if matched_tags:
            for tag in matched_tags:
                tag_index[tag].append(file_info)
            auto_tagged_count += 1
            print(f"  🎯 자동 태그(기존 매칭): {file_info['name']} → {', '.join(['#'+t for t in matched_tags])}")
        else:
            # --- 2단계: 본문에서 핵심 키워드 추출하여 새 태그 생성 ---
            new_tags = extract_keywords(file_info["full_content"], stop_words)
            if new_tags:
                for tag in new_tags:
                    tag_index[tag].append(file_info)
                new_tag_count += 1
                print(f"  🆕 새 태그 생성: {file_info['name']} → {', '.join(['#'+t for t in new_tags])}")
            else:
                still_untagged.append(file_info)
    
    if auto_tagged_count > 0:
        print(f"\n✨ {auto_tagged_count}개의 미분류 문서 → 기존 태그 자동 부여 완료")
    if new_tag_count > 0:
        print(f"🆕 {new_tag_count}개의 미분류 문서 → 새 태그 자동 생성 완료")
    if still_untagged:
        print(f"⚠️ {len(still_untagged)}개의 문서는 키워드를 추출하지 못해 여전히 미분류입니다.")
        
    return tag_index, still_untagged

def extract_keywords(text, stop_words, top_n=2):
    """
    텍스트에서 가장 자주 등장하는 핵심 명사/키워드를 추출합니다.
    마크다운 문법과 불용어를 제거한 뒤, 2글자 이상의 단어 빈도를 분석합니다.
    """
    from collections import Counter
    
    # 마크다운 문법, URL, 특수문자 제거
    clean = re.sub(r'https?://\S+', '', text)
    clean = re.sub(r'[#*_\-\[\]\(\)\{\}\|`>!~=+]', ' ', clean)
    clean = re.sub(r'[0-9]+', ' ', clean)
    clean = re.sub(r'\s+', ' ', clean).strip()
    
    # 공백으로 토큰화
    words = clean.split()
    
    # 필터: 2글자 이상, 불용어 제외, 순수 영문 1글자 제외
    filtered = []
    for w in words:
        w_lower = w.lower().strip()
        if len(w_lower) >= 2 and w_lower not in stop_words:
            # 순수 한글 또는 영문 단어만 (혼합도 허용)
            if re.match(r'^[가-힣a-zA-Z]+$', w_lower):
                filtered.append(w_lower)
    
    if not filtered:
        return []
    
    # 빈도 카운트 후 상위 N개 반환
    counter = Counter(filtered)
    top_keywords = [word for word, count in counter.most_common(top_n) if count >= 2]
    
    return top_keywords

def generate_graph_data(tag_index):
    """태그와 문서를 우주 테마(Galaxy Theme) 노드와 엣지 데이터로 변환합니다."""
    nodes = []
    edges = []
    document_db = {}
    
    node_id_map = {}
    current_node_id = 1
    
    # 1. 중앙 노드 (지구 이미지)
    nodes.append({
        "id": 0,
        "label": "My Universe",
        "group": "center",
        "shape": "image",
        "image": "https://cdn.jsdelivr.net/gh/twitter/twemoji@14.0.2/assets/svg/1f30d.svg",
        "size": 70,
        "font": {"size": 22, "face": "Pretendard, sans-serif", "color": "#FDFBD4", "strokeWidth": 2, "strokeColor": "#0F172A", "vadjust": 10},
        "shadow": {"enabled": True, "color": "rgba(96, 165, 250, 0.6)", "size": 40, "x": 0, "y": 0}
    })
    
    # 2. 태그(주제) 노드 생성 (빛나는 항성)
    for tag, files in tag_index.items():
        tag_id = current_node_id
        node_id_map[f"tag_{tag}"] = tag_id
        current_node_id += 1
        
        ufo_size = min(50, max(28, 20 + len(files) * 2))
        
        nodes.append({
            "id": tag_id,
            "label": f"#{tag}",
            "group": "tags",
            "shape": "image",
            "image": "data:image/svg+xml," + __import__('urllib.parse', fromlist=['quote']).quote('<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 64 44"><ellipse cx="32" cy="18" rx="12" ry="10" fill="#A8D8EA"/><ellipse cx="32" cy="16" rx="9" ry="7" fill="#CBE4F3" opacity="0.6"/><ellipse cx="32" cy="24" rx="28" ry="10" fill="#B0BEC5"/><ellipse cx="32" cy="23" rx="28" ry="9" fill="#CFD8DC"/><ellipse cx="32" cy="22" rx="26" ry="7" fill="#ECEFF1"/><ellipse cx="32" cy="28" rx="22" ry="5" fill="#90A4AE" opacity="0.5"/><circle cx="14" cy="24" r="2.5" fill="#FF6B6B"/><circle cx="23" cy="27" r="2.5" fill="#48DBFB"/><circle cx="32" cy="28" r="2.5" fill="#FECA57"/><circle cx="41" cy="27" r="2.5" fill="#48DBFB"/><circle cx="50" cy="24" r="2.5" fill="#FF6B6B"/><ellipse cx="28" cy="14" rx="4" ry="3" fill="white" opacity="0.35"/></svg>'),
            "size": ufo_size,
            "title": f"<div style='color:white'><b>#{tag}</b> <br>\u2728 \uad00\ub828 \ubb38\uc11c: {len(files)}\uac1c</div>",
            "font": {"size": 20, "face": "Pretendard, sans-serif", "color": "#FFFFFF", "strokeWidth": 3, "strokeColor": "#000000", "vadjust": 8},
            "shadow": {"enabled": True, "color": "rgba(165, 180, 252, 0.5)", "size": 20, "x": 0, "y": 0}
        })
        
        # 중앙 태양과 각 항성(태그)간 연결 (빛줄기)
        edges.append({
            "from": 0,
            "to": tag_id,
            "color": {"color": "rgba(252, 211, 77, 0.25)", "highlight": "rgba(252, 211, 77, 1.0)"},
            "width": 3,
            "length": 300
        })
        
    # 3. 마크다운 파일(문서) 노드 생성 (작은 위성/별빛)
    file_node_created = set()
    
    for tag, files in tag_index.items():
        tag_id = node_id_map[f"tag_{tag}"]
        
        for file_info in files:
            file_name = file_info["name"]
            
            if file_name not in file_node_created:
                file_id = current_node_id
                node_id_map[file_name] = file_id
                current_node_id += 1
                
                document_db[file_id] = {
                    "title": file_name,
                    "content": file_info["full_content"]
                }
                
                # 툴팁: 다크 테마 커스텀 HTML
                tooltip_html = f"<div style='color:#F1F5F9'><b>{file_name}</b><hr style='border:none;border-top:1px solid #475569;margin:8px 0;'><small style='color:#CBD5E1'>{file_info['summary']}</small><br><br><span style='color:#38BDF8; font-weight:bold'>✨ 더블클릭하여 문서 탐사하기</span></div>"
                
                display_label = file_name.replace('.md', '')
                if len(display_label) > 16:
                    display_label = display_label[:15] + '..'
                    
                nodes.append({
                    "id": file_id,
                    "label": display_label,
                    "group": "files",
                    "shape": "dot", # 상자 대신 원형 빛 뭉치로 변경
                    "size": 16,
                    "title": tooltip_html,
                    "font": {"size": 14, "face": "Pretendard, sans-serif", "color": "#E2E8F0", "strokeWidth": 2, "strokeColor": "#000000", "vadjust": 15},
                    "color": {
                        "background": "#F1F5F9", 
                        "border": "#FFFFFF",
                        "highlight": {"background": "#FFFFFF", "border": "#FFFFFF"}
                    },
                    "shadow": {"enabled": True, "color": "rgba(255, 255, 255, 0.4)", "size": 10, "x": 0, "y": 0}
                })
                file_node_created.add(file_name)
            else:
                file_id = node_id_map[file_name]
                
            # 태그(항성)와 문서(위성) 연결선 (희미한 궤도 빛줄기)
            edges.append({
                "from": tag_id,
                "to": file_id,
                "color": {"color": "rgba(148, 163, 184, 0.25)", "highlight": "rgba(56, 189, 248, 1.0)"},
                "width": 1.5,
                "length": 150
            })

    return nodes, edges, document_db

def save_to_html(nodes, edges, doc_db, output_path):
    """우주 테마(Galaxy Theme)가 적용된 인터랙티브 HTML 파일을 생성합니다."""
    
    print("\n[다크 우주 테마 HTML 그래픽 렌더링 중...]")
    
    nodes_json = json.dumps(nodes, ensure_ascii=False)
    edges_json = json.dumps(edges, ensure_ascii=False)
    doc_db_json = json.dumps(doc_db, ensure_ascii=False)
    
    html_content = f"""<!DOCTYPE html>
<html lang="ko">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Ontology Galaxy Map</title>
    <link href="https://cdn.jsdelivr.net/gh/orioncactus/pretendard/dist/web/static/pretendard.css" rel="stylesheet" />
    <script type="text/javascript" src="https://unpkg.com/vis-network/standalone/umd/vis-network.min.js"></script>
    <script src="https://cdn.jsdelivr.net/npm/marked/marked.min.js"></script>

    <style>
        body {{
            margin: 0;
            padding: 0;
            font-family: 'Pretendard', sans-serif;
            /* 깊은 밤하늘 우주 배경 (Radial Gradient) */
            background: radial-gradient(circle at center, #1E1B4B 0%, #0B0F19 50%, #000000 100%);
            overflow: hidden;
            color: #E2E8F0; /* 기본 글씨색을 밝게 */
        }}
        #mynetwork {{
            width: 100vw;
            height: 100vh;
            border: none;
            /* 네트워크 뒤 배경에 흐릿한 은하수 이미지나 추가 효과를 넣기 위해 투명 적용 */
            background: transparent; 
        }}
        
        #loading {{
            position: absolute;
            top: 50%; left: 50%;
            transform: translate(-50%, -50%);
            font-size: 22px;
            color: #94A3B8;
            pointer-events: none;
            z-index: 10;
            text-shadow: 0 0 10px rgba(148, 163, 184, 0.5);
        }}
        
        /* 컨트롤 패널 - 다크 글래스모피즘 효과 */
        .control-panel {{
            position: absolute;
            top: 24px; left: 24px;
            background: rgba(15, 23, 42, 0.5); /* 반투명 암회색 */
            backdrop-filter: blur(12px);
            -webkit-backdrop-filter: blur(12px);
            border: 1px solid rgba(255, 255, 255, 0.1);
            padding: 20px 24px;
            border-radius: 16px;
            box-shadow: 0 8px 32px rgba(0,0,0,0.5);
            z-index: 20;
            pointer-events: auto;
        }}
        .control-panel h1 {{
            margin: 0 0 8px 0;
            font-size: 20px;
            color: #F8FAFC;
            letter-spacing: 0.5px;
            font-weight: 700;
        }}
        .control-panel p {{
            margin: 4px 0;
            font-size: 14px;
            color: #94A3B8;
        }}
        .control-panel .highlight {{
            color: #38BDF8; /* 밝은 하늘색 강조 */
            font-weight: 600;
        }}
        
        /* vis.js 내장 툴팁 스타일도 다크모드/우주풍 커스텀 */
        .vis-tooltip {{
            background: rgba(15, 23, 42, 0.9) !important;
            backdrop-filter: blur(12px) !important;
            -webkit-backdrop-filter: blur(12px) !important;
            border: 1px solid rgba(56, 189, 248, 0.3) !important;
            border-radius: 12px !important;
            box-shadow: 0 12px 30px rgba(0,0,0,0.7) !important;
            padding: 16px 20px !important;
            font-family: 'Pretendard', sans-serif !important;
            font-size: 14px !important;
            color: #F8FAFC !important;
            max-width: 320px !important;
            white-space: normal !important;
            line-height: 1.6 !important;
            pointer-events: none !important;
        }}
        
        /* 모바일 대응 툴팁 최적화 */
        @media (max-width: 768px) {{
            .vis-tooltip {{
                max-width: 250px !important;
                padding: 12px 16px !important;
                font-size: 13px !important;
            }}
            .vis-tooltip b {{ font-size: 14px !important; }}
            .vis-tooltip hr {{ margin: 6px 0 !important; }}
        }}
        
        /* ⬇ 다크 테마 뷰어 모달(문서 모니터창) 스타일 ⬇ */
        #docModalOverlay {{
            display: none;
            position: fixed;
            top: 0; left: 0; right: 0; bottom: 0;
            background-color: rgba(0,0,0,0.7); /* 더 어두운 뒷배경 */
            z-index: 1000;
            opacity: 0;
            transition: opacity 0.4s cubic-bezier(0.16, 1, 0.3, 1);
            backdrop-filter: blur(8px); /* 우주 배경 블러 */
        }}
        #docModalOverlay.show {{
            display: block; opacity: 1;
        }}
        
        #docModalWindow {{
            position: absolute;
            top: 50%; left: 50%;
            transform: translate(-50%, -50%) scale(0.9);
            
            /* 유리 모니터 느낌 */
            background: rgba(15, 23, 42, 0.85);
            backdrop-filter: blur(20px);
            -webkit-backdrop-filter: blur(20px);
            border: 1px solid rgba(255, 255, 255, 0.1);
            
            width: 85%; max-width: 960px;
            height: 90%; max-height: 850px;
            border-radius: 20px;
            box-shadow: 0 25px 50px -12px rgba(0, 0, 0, 0.5), inset 0 0 20px rgba(56, 189, 248, 0.1);
            display: flex;
            flex-direction: column;
            transition: transform 0.4s cubic-bezier(0.16, 1, 0.3, 1);
        }}
        #docModalOverlay.show #docModalWindow {{
            transform: translate(-50%, -50%) scale(1);
        }}
        
        #modalHeader {{
            padding: 24px 30px;
            border-bottom: 1px solid rgba(255, 255, 255, 0.08);
            display: flex;
            justify-content: space-between;
            align-items: center;
            background: rgba(255, 255, 255, 0.02);
            border-radius: 20px 20px 0 0;
        }}
        #modalTitle {{
            margin: 0; font-size: 22px; font-weight: 700;
            color: #F1F5F9;
            text-shadow: 0 0 10px rgba(255, 255, 255, 0.1);
        }}
        #closeBtn {{
            background: none; border: none; font-size: 28px;
            cursor: pointer; color: #94A3B8;
            transition: all 0.2s;
            width: 40px; height: 40px;
            display: flex; align-items: center; justify-content: center;
            border-radius: 50%;
        }}
        #closeBtn:hover {{ 
            color: #F8FAFC; 
            background: rgba(239, 68, 68, 0.2); 
            text-shadow: 0 0 8px rgba(239, 68, 68, 0.5);
        }}
        
        /* 스크롤바 커스텀 (다크 테마용) */
        #modalContent::-webkit-scrollbar {{ width: 8px; }}
        #modalContent::-webkit-scrollbar-track {{ background: rgba(0,0,0,0.1); border-radius: 4px; }}
        #modalContent::-webkit-scrollbar-thumb {{ background: rgba(148, 163, 184, 0.3); border-radius: 4px; }}
        #modalContent::-webkit-scrollbar-thumb:hover {{ background: rgba(148, 163, 184, 0.6); }}

        #modalContent {{
            padding: 40px;
            overflow-y: auto;
            flex-grow: 1;
            font-size: 17px;
            line-height: 1.7;
            color: #CBD5E1; /* 파스텔톤 밝은 회색 텍스트 */
        }}
        
        /* 마크다운 파서 스타일 렌더링 (다크 테마 최적화) */
        #modalContent h1, #modalContent h2, #modalContent h3 {{ color: #F8FAFC; margin-top: 1.8em; font-weight: 700; }}
        #modalContent h1 {{ border-bottom: 1px solid rgba(255, 255, 255, 0.1); padding-bottom: 12px; }}
        #modalContent h2 {{ color: #E2E8F0; }}
        #modalContent a {{ color: #38BDF8; text-decoration: none; border-bottom: 1px dashed rgba(56, 189, 248, 0.4); }}
        #modalContent a:hover {{ color: #7DD3FC; border-bottom-style: solid; }}
        #modalContent blockquote {{ 
            border-left: 4px solid #818CF8; 
            padding-left: 18px; 
            color: #94A3B8; 
            background: rgba(129, 140, 248, 0.05); /* 블록 인용구 약한 배경색 */
            padding: 10px 18px;
            border-radius: 0 8px 8px 0;
            margin-left: 0; font-style: italic; 
        }}
        #modalContent strong {{ color: #FFFFFF; font-weight: 700; text-shadow: 0 0 1px rgba(255,255,255,0.3); }}
        #modalContent code {{
            background: rgba(0, 0, 0, 0.4);
            padding: 2px 6px; border-radius: 4px; color: #FCA5A5; font-size: 0.9em;
            border: 1px solid rgba(255, 255, 255, 0.05);
        }}
        #modalContent pre code {{
            display: block; padding: 16px; border-radius: 8px;
            background: rgba(0, 0, 0, 0.6); color: #E2E8F0; overflow-x: auto;
        }}
        #modalContent ul, #modalContent ol {{ padding-left: 20px; }}
        #modalContent li {{ margin-bottom: 8px; }}

    </style>
</head>
<body>
    <div class="control-panel">
        <h1>💫 Galaxy Ontology Map</h1>
        <p>마우스 스크롤: 맵 확대/축소</p>
        <p>드래그: 뷰 이동 & 별자리 끌어오기</p>
        <p>UFO·별 클릭: 연결선 강조 표시</p>
        <p class="highlight">✨ 작은 별(문서) 더블클릭: 원본 읽기</p>
    </div>
    
    <div id="loading">✨ 우주 정거장 부팅 및 성간 맵핑 중...</div>
    <div id="mynetwork"></div>
    
    <div id="docModalOverlay">
        <div id="docModalWindow">
            <div id="modalHeader">
                <h2 id="modalTitle">File Name</h2>
                <button id="closeBtn">&times;</button>
            </div>
            <div id="modalContent"></div>
        </div>
    </div>
    
    <script type="text/javascript">
        var nodesData = {nodes_json};
        var edgesData = {edges_json};
        var docDb = {doc_db_json};
        
        var nodes = new vis.DataSet(nodesData);
        var edges = new vis.DataSet(edgesData);
        var data = {{ nodes: nodes, edges: edges }};
        
        var options = {{
            nodes: {{ 
                borderWidth: 1, 
                borderWidthSelected: 3, // 선택 시 두껍게 발광
                color: {{ highlight: {{ border: '#FFFFFF' }} }}
            }},
            edges: {{ 
                smooth: {{ type: 'continuous', forceDirection: 'none' }},
                selectionWidth: 4 // 선 선택시 굵기
            }},
            interaction: {{ 
                hover: true, tooltipDelay: 200, zoomView: true, dragView: true,
                hideEdgesOnDrag: false // 스크롤/드래그 시에도 멋지게 선을 유지
            }},
            physics: {{
                // ★ 우주의 무중력 느낌을 위한 파라미터 튜닝 ★
                forceAtlas2Based: {{ 
                    gravitationalConstant: -70, // 음수값이 클수록 더 넓게 튕겨나감
                    centralGravity: 0.003,      // 중심(화면 가운데)으로 끌어당기는 힘 (매우 약하게)
                    springLength: 200,          // 노드간 연결선(가스)의 기본 길이
                    springConstant: 0.02,       // 튕기는 탄성. 낮을수록 흐물흐물하고 여유롭게 움직임
                    damping: 0.1                // 브레이크. 낮을수록 오래 부드럽게 움직임
                }},
                maxVelocity: 40, minVelocity: 0.1, solver: 'forceAtlas2Based',
                stabilization: {{ enabled: true, iterations: 1000, updateInterval: 100, onlyDynamicEdges: false, fit: true }}
            }}
        }};
        
        var container = document.getElementById("mynetwork");
        var network = new vis.Network(container, data, options);
        
        network.on("stabilizationIterationsDone", function () {{
            document.getElementById("loading").style.display = "none";
        }});
        
        // --- 모달 로직 (뷰어) ---
        const modalOverlay = document.getElementById('docModalOverlay');
        const modalTitle = document.getElementById('modalTitle');
        const modalContent = document.getElementById('modalContent');
        const closeBtn = document.getElementById('closeBtn');
        
        network.on("doubleClick", function (params) {{
            if (params.nodes.length > 0) {{
                const nodeId = params.nodes[0];
                const docInfo = docDb[nodeId];
                if(docInfo) {{ openModal(docInfo.title, docInfo.content); }}
            }}
        }});
        
        function openModal(title, textContent) {{
            modalTitle.textContent = title;
            modalContent.innerHTML = marked.parse(textContent); 
            modalOverlay.classList.add('show');
            document.body.style.overflow = 'hidden'; 
        }}
        
        // --- 툴팁 HTML 활성화 및 모바일 최적화 로직 ---
        let tooltipTimer = null;
        
        // vis.js는 기본적으로 title 내의 HTML을 문자열로만 취급하려 하므로,
        // DOM 요소로 변환해주는 과정이 필요합니다.
        nodes.forEach(function(node) {{
            if (node.title) {{
                const wrapper = document.createElement('div');
                wrapper.innerHTML = node.title;
                node.title = wrapper;
                nodes.update(node);
            }}
        }});

        network.on("showTooltip", function (params) {{
            // 모바일 환경 체크
            const isMobile = /iPhone|iPad|iPod|Android/i.test(navigator.userAgent);
            
            if (isMobile) {{
                // 모바일에서는 수동으로 일정 시간 뒤에 숨김 (시야 확보)
                if (tooltipTimer) clearTimeout(tooltipTimer);
                tooltipTimer = setTimeout(() => {{
                    const tooltip = document.querySelector('.vis-tooltip');
                    if (tooltip) tooltip.style.visibility = 'hidden';
                }}, 3000); // 3초 뒤 자동 소멸
            }}
        }});

        network.on("hideTooltip", function () {{
            if (tooltipTimer) clearTimeout(tooltipTimer);
        }});
        
        network.on("dragStart", function() {{
            // 드래그 시작 시 즉시 툴팁 숨김
            const tooltip = document.querySelector('.vis-tooltip');
            if (tooltip) tooltip.style.visibility = 'hidden';
        }});

        function closeModal() {{
            modalOverlay.classList.remove('show');
            document.body.style.overflow = '';
        }}
        
        closeBtn.addEventListener('click', closeModal);
        modalOverlay.addEventListener('click', function(e) {{
            if(e.target === modalOverlay) closeModal();
        }});
        document.addEventListener('keydown', function(e) {{
            if(e.key === 'Escape' && modalOverlay.classList.contains('show')) closeModal();
        }});
    </script>
</body>
</html>
"""
    try:
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(html_content)
        print(f"✅ 우주(Galaxy) 테마의 시각화 지도가 생성되었습니다: {output_path}")
    except Exception as e:
        print(f"HTML 파일 작성 중 오류 발생: {e}")

def main():
    tag_index, untagged_files = group_files_by_tags(DOCS_DIR)
    if not tag_index and not untagged_files:
        print("처리할 마크다운 파일이 없습니다.")
        return
    print(f"총 {len(tag_index)}개의 태그 그룹(은하) 발견.")
    
    # 태그 없는 문서에 자동 태그 부여
    if untagged_files:
        print(f"\n🔍 {len(untagged_files)}개의 미분류 문서 발견. 본문 내용 기반 자동 태그 부여 시도 중...")
        tag_index, still_untagged = auto_tag_untagged_files(tag_index, untagged_files)
    
    nodes, edges, doc_db = generate_graph_data(tag_index)
    save_to_html(nodes, edges, doc_db, OUTPUT_HTML)

if __name__ == "__main__":
    main()
