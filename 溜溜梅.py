import gradio as gr
import sqlite3
import time
# import openai
import json
import tkinter as tk
from tkinter import messagebox
import datetime
import pandas as pd

# 导入功能有关的函数
def read_txts(txts):
    txt_list = []
    if txts is not None:
        for txt in txts:
            path = txt.name
            with open(path, 'r', encoding='utf-8') as f:
                content = f.read()
                txt_list.append(content)
    return txt_list

def split_string_into_lists(input_string):
    split_strings = input_string.split('@@')
    ask = []
    answer = []
    for i, text in enumerate(split_strings):
        if i % 2 == 0:
            ask.append(text.strip())
        else:
            answer.append(text.strip())
    return ask, answer

# 需要加进度条
def preprocess_txts(txt_list, progress=gr.Progress()):
    progress(0, desc='正在读取和解析文件...')
    qa_dict = {}
    if txt_list is not None:
        for txt in progress.tqdm(txt_list):
            ask_list, answer_list = split_string_into_lists(txt)
            if len(ask_list) == len(answer_list):
                for ask, answer in zip(ask_list, answer_list):
                    qa_dict[ask] = answer
            else:
                gr.Error('上传的txt格式有问题，问题和回答对应不起来')
    return qa_dict

def read_jsons(jsons):
    json_list = []
    if jsons is not None:
        for j in jsons:
            path = j.name
            with open(path, "r", encoding="utf-8") as json_file:
                data = json.load(json_file)
            json_list.append(data)
    return json_list[:2], json_list


def add_prompt_id(upload_kuo_file):
    added_pormpt_id_list = []
    for json_file in upload_kuo_file:
        json_path = json_file.name
        with open(json_path, 'r', encoding='utf-8') as file:
            data = json.load(file)
            group_id_count = {}
            for item in data:
                group_id = item['group_Id'][:7]
                if group_id not in group_id_count:
                    group_id_count[group_id] = 1
                else:
                    group_id_count[group_id] += 1
                prompt_id = f"{group_id}{group_id_count[group_id]:05}"
                item['prompt_Id'] = prompt_id
        added_pormpt_id_list.append(data)
    return added_pormpt_id_list


def import_kuo(project_name, knowledge_name, cluster_name, json_kuo_list):
    conn = sqlite3.connect('pufa-sqlite.db')
    cursor = conn.cursor() 
    for lists in json_kuo_list:
        for i in lists:
            prompt_data = ( i['prompt_Ask'], i['prompt_Answer'],i['prompt_Id'])
            cursor.execute('INSERT INTO Prompt ( Prompt_Ask, Prompt_Answer,prompt_Id) VALUES ( ?, ?, ?)', prompt_data)
            project_data = (i['project_Id'], i['project_Name'],i['knowledge_Id'],i['group_Id'],i['cluster_Id'],i['prompt_Id'])
            cursor.execute('INSERT INTO Project (project_Id, project_Name,knowledge_Id,group_Id,cluster_Id,prompt_Id) VALUES (?, ?, ?, ?, ?, ?)', project_data)
    conn.commit()
    conn.close()
    return '导入成功！'

def preview_in_textbox(qa_dict):
    first_10_items = {k: qa_dict[k] for k in list(qa_dict)[:10]}
    return first_10_items

# 需要增加进度条
def generate_data_json(project_name, knowledge_name, cluster_name, qa_dict):
    conn = sqlite3.connect('pufa-sqlite.db')
    cursor = conn.cursor()
    cursor.execute("SELECT prompt_Id FROM Project")
    results = cursor.fetchall()
    if not results:
        prompt_id_num = 100000
    else:
        max_index = max(results, key=lambda x: int(x[0]))
        max_index=str(max_index[0])
        max_index = max_index[:-5]+'00000'
        prompt_id_num = int(max_index) + 100000
    prompt_id = "{:012}".format(prompt_id_num)
    
    project_mapping = {'浦发': '1'}
    knowledge_mapping = {'页面知识点': '1', '功能点': '2', '链': '3'}
    cluster_mapping = {'': '0', '邮件相关': '1', '新建申请页面优化字段相关': '2', '同步数据相关': '3', '需求报表相关': '4'}

    if project_name not in project_mapping:
        raise gr.Error("请正确选择项目")
    if knowledge_name not in knowledge_mapping:
        raise gr.Error("请正确选择问答对类型")
    if cluster_name not in cluster_mapping:
        raise gr.Error("请正确选择问答对所属簇")

    data_json = []

    for ask, answer in qa_dict.items():
        data_entry = {
            "project_Id": project_mapping[project_name],
            "project_Name": project_name,
            "knowledge_Id": knowledge_mapping[knowledge_name],
            "knowledge_Name": knowledge_name,
            "cluster_Id": cluster_mapping[cluster_name],
            "group_Id": prompt_id,
            "prompt_Id": prompt_id,
            "prompt_Ask": ask,
            "prompt_Answer": answer,
            "cluster_Ask": "",
            "cluster_Answer": ""
        }
        data_json.append(data_entry)
        prompt_id_num += 100000
        prompt_id = "{:012}".format(prompt_id_num)
    
    for entry in data_json:

        cluster_data = (entry['cluster_Id'], entry['cluster_Ask'], entry['cluster_Answer'])
        cursor.execute('INSERT INTO Cluster (cluster_Id, cluster_Ask, cluster_Answer) VALUES (?, ?, ?)', cluster_data)

        knowledge_data = (entry['knowledge_Id'], entry['knowledge_Name'])
        cursor.execute('INSERT INTO Knowledge (knowledge_Id, knowledge_Name) VALUES (?, ?)', knowledge_data)

        prompt_data = ( entry['prompt_Ask'], entry['prompt_Answer'],entry['prompt_Id'])
        cursor.execute('INSERT INTO Prompt ( Prompt_Ask, Prompt_Answer,prompt_Id) VALUES ( ?, ?, ?)', prompt_data)

        project_data = (entry['project_Id'], entry['project_Name'],entry['knowledge_Id'],entry['group_Id'],entry['cluster_Id'],entry['prompt_Id'])
        cursor.execute('INSERT INTO Project (project_Id, project_Name,knowledge_Id,group_Id,cluster_Id,prompt_Id) VALUES (?, ?, ?, ?, ?, ?)', project_data)

    conn.commit()
    conn.close()
    if cluster_name == '':
        return '导入成功，由于未选择簇，cluster_id全为0'
    else:
        return '导入成功'

def kuo_function(project_name, knowledge_name, cluster_name, json_kuo_list):
    # 在此函数中创建确认弹出框
    root = tk.Tk()
    root.withdraw()# 隐藏主窗口
    top = tk.Toplevel(root)
    top.withdraw() 
    top.attributes('-topmost', 1) 
    result = messagebox.askokcancel("确认", "您确定要执行此操作吗？",parent=top)

    if result:
        import_kuo(project_name, knowledge_name, cluster_name, json_kuo_list)
        return "操作已执行"
    else:
        # 如果用户点击"取消"，返回相应信息
        return "操作已取消"
    
def daoru_function(project_name, knowledge_name, cluster_name, qa_dict):
    root=tk.Tk()
    root.withdraw()  # 隐藏主窗口
    top = tk.Toplevel(root)
    top.withdraw() 
    top.attributes('-topmost', 1) 
    result = messagebox.askokcancel("确认", "您确定要执行此操作吗？", parent=top)

    if result:
        generate_data_json(project_name, knowledge_name, cluster_name, qa_dict)
        return "操作已执行"
    else:
        # 如果用户点击"取消"，返回相应信息
        return "操作已取消"
    
# 扩写功能有关的函数
def get_completion(prompt, system_message, model='gpt-3.5-turbo-16k', temperature=0): 
    openai.api_key = "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"
    start_time = time.time() 
    max_retries = 3
    retries = 0
    while retries < max_retries:
        try:
            response = openai.ChatCompletion.create(
                model='gpt-3.5-turbo-16k',
                messages=[
                    {'role': 'system', 'content': f'{system_message}'},
                    {'role': 'user', 'content': f'{prompt}'}],
                temperature=0,
                stream=True)
            break
        except Exception as e:
            gr.Info(f'发生错误：{e}\n20秒后重试')
            retries += 1
            time.sleep(20)
    if retries == max_retries:
        gr.Error('已达最大重试次数，程序停止运行')
    collected_messages = []
    for chunk in response:
        chunk_message = chunk['choices'][0]['delta']
        collected_messages.append(chunk_message)
        full_reply_content = ''.join([m.get('content', '') for m in collected_messages])
        yield full_reply_content
        
def pkuo(index, pkuo_system_msg, pkuo_search_ids, pkuo_gptoutput):
    promptid = pkuo_search_ids[index]
    ask, answer = search_id(promptid)
    get_completion(ask, pkuo_system_msg)

    openai.api_key = "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"
    start_time = time.time() 
    max_retries = 3
    retries = 0
    while retries < max_retries:
        try:
            response = openai.ChatCompletion.create(
                model='gpt-3.5-turbo-16k',
                messages=[
                    {'role': 'system', 'content': f'{pkuo_system_msg}'},
                    {'role': 'user', 'content': f'{ask}'}],
                temperature=0,
                stream=True)
            break
        except Exception as e:
            gr.Info(f'发生错误：{e}\n20秒后重试')
            retries += 1
            time.sleep(20)
    if retries == max_retries:
        gr.Error('已达最大重试次数，程序停止运行')
    collected_messages = []
    for chunk in response:
        chunk_message = chunk['choices'][0]['delta']
        collected_messages.append(chunk_message)
        full_reply_content = ''.join([m.get('content', '') for m in collected_messages])
        yield full_reply_content      

def search_id(promptid):
    conn = sqlite3.connect('pufa-sqlite.db')
    cursor = conn.cursor()
    try:
        cursor.execute('SELECT prompt_Ask, prompt_Answer FROM Prompt WHERE prompt_Id = ?', (str(promptid),))
        result = cursor.fetchall()
        if result != []:
            ask = result[0][0]
            answer = result[0][1]
        conn.commit()
        conn.close()
        return ask, answer
    except Exception as e:
        return '', ''
    
def search_groupid(promptid):
    conn = sqlite3.connect('pufa-sqlite.db')
    cursor = conn.cursor()
    cursor.execute('SELECT group_Id FROM Project WHERE prompt_Id = ?', (str(promptid),))
    result = cursor.fetchall()
    conn.commit()
    conn.close()
    return result
        
def outport(promptid, kuo_searched_answer, kuo_gptoutput, json_name):
    current_time = datetime.datetime.now()
    current_time = current_time.strftime("%Y-%m-%d-%H-%M-%S")
    kuo_qa_list = []
    output_lines = kuo_gptoutput.splitlines()
    for line in output_lines:
        kuo_qa_dict = {
            "group_Id": promptid,
            "prompt_Ask": line.strip(),
            "prompt_Answer": kuo_searched_answer.strip()
        }
        kuo_qa_list.append(kuo_qa_dict)
    output_filename = f"{json_name+str(current_time)}.json"
    with open(output_filename, 'w', encoding='utf-8') as json_file:
        json.dump(kuo_qa_list, json_file, ensure_ascii=False, indent=4)
    return f'导出成功：{json_name+str(current_time)}.json'

def display_result(index, pkuo_search_ids, pkuo_gptoutput, pkuo_result):
    conn = sqlite3.connect('pufa-sqlite.db')
    cursor = conn.cursor()
    id_ = pkuo_search_ids[index]
    cursor.execute('SELECT prompt_Id FROM Project WHERE id =?', (id_,))
    promptid = cursor.fetchall()
    conn.commit()
    conn.close()
    _, answer = search_id(promptid[0][0])
    groupid = search_groupid(promptid[0][0])
    groupid = groupid[0][0]
    
    output_lines = pkuo_gptoutput.splitlines()
    for line in output_lines:
        pkuo_qa_dict = {
            "group_Id": groupid,
            "prompt_Ask": line.strip(),
            "prompt_Answer": answer.strip()
        }
        pkuo_result.append(pkuo_qa_dict)
    return pkuo_result

def index_addone(index):
    return index + 1

def update_index(index, pkuo_search_ids):
    if index < len(pkuo_search_ids)-1:
        return index + 1
    else:
        return index
    
def stop_it():
    return 999, 999

def pkuo_outport(pkuo_result, pkuo_json_name):
    current_time = datetime.datetime.now()
    current_time = current_time.strftime("%Y-%m-%d-%H-%M-%S")
    output_filename = f'{pkuo_json_name+str(current_time)}.json'
    with open(output_filename, 'w', encoding='utf-8') as json_file:
        json.dump(pkuo_result, json_file, ensure_ascii=False, indent=4)
    return f'导出成功：{pkuo_json_name+str(current_time)}.json'

def fill_more_info(kuo_dict_list):
    full_dict_list = []
    conn = sqlite3.connect('pufa-sqlite.db')
    cursor = conn.cursor()
    for kuo_dict in kuo_dict_list:
        group_id = kuo_dict["group_Id"]
        prompt_ask = kuo_dict["prompt_Ask"]
        prompt_answer = kuo_dict["prompt_Answer"]
        
        cursor.execute("SELECT project_Id FROM Project WHERE prompt_id = ?", (group_id,))
        result_project_Id = cursor.fetchone()
        cursor.execute("SELECT project_Name FROM Project WHERE prompt_id = ?", (group_id,))
        result_project_Name = cursor.fetchone()
        cursor.execute("SELECT knowledge_Id FROM Project WHERE prompt_id = ?", (group_id,))
        result_knowledge_Id = cursor.fetchone()
        cursor.execute("SELECT cluster_Id FROM Project WHERE prompt_id = ?", (group_id,))
        result_cluster_Id = cursor.fetchone()
        full_dict = {
            "project_Id": result_project_Id[0],
            "project_Name": result_project_Name[0],
            "knowledge_Id": result_knowledge_Id[0],
            "cluster_Id": result_cluster_Id[0],
            "group_Id": group_id,
            "prompt_Ask": prompt_ask,
            "prompt_Answer": prompt_answer
        }
        full_dict_list.append(full_dict)
    conn.commit()
    conn.close()
    return full_dict_list

def process_kuo_json(json_name):
    if json_name.startswith("导出成功："):
        json_name = json_name[len("导出成功："):]
    json_path = json_name
    with open(json_path, "r", encoding="utf-8") as json_file:
        data = json.load(json_file)
    filled_data = fill_more_info(data)
    with open(json_path, 'w', encoding='utf-8') as json_file:
        json.dump(filled_data, json_file, ensure_ascii=False, indent=4)
        
def panduan_promax(select_knowledge, select_cluster):
    knowledge_mapping = {'页面知识点': '1', '功能点': '2', '链': '3'}
    cluster_mapping = {'邮件相关': '1', '新建申请页面优化字段相关': '2', '同步数据相关': '3', '需求报表相关': '4'}
    if select_knowledge not in knowledge_mapping and select_cluster not in cluster_mapping:
        raise gr.Error("请至少选择一个选择问答对类型或问答对的簇")
    elif select_knowledge in knowledge_mapping and select_cluster not in cluster_mapping:
        a=knowledge_mapping[select_knowledge]
        result=search_knowledge(a)
    elif select_knowledge not in knowledge_mapping and select_cluster in cluster_mapping:
        b=cluster_mapping[select_cluster]
        result=search_cluster(b)
    else:
        a1=knowledge_mapping[select_knowledge]
        b1=cluster_mapping[select_cluster]
        result=search(a1,b1)
    conn = sqlite3.connect('pufa-sqlite.db')
    cursor = conn.cursor()
    i=[]
    for items in result:
        cursor.execute('SELECT group_Id FROM Project WHERE id =? ',(items,))
        gid = cursor.fetchone()
        cursor.execute('SELECT prompt_Id FROM Project WHERE group_Id = ?',(gid[0],))
        num=cursor.fetchall()
        num=len(num)
        print(num,gid)
        if num==1:
            i.append(items)
    return i

# 导出功能有关的函数    
def outport_func(indice, outport_file_name):
    result = []
    conn = sqlite3.connect('pufa-sqlite.db')
    cursor = conn.cursor()
    for i in indice:
        cursor.execute('SELECT prompt_Ask FROM Prompt WHERE id =?', (i,))
        ask = cursor.fetchall()
        cursor.execute('SELECT prompt_Answer FROM Prompt WHERE id =?', (i,))
        answer = cursor.fetchall()
        entry = {
            "instruction": ask[0][0],
            "output": answer[0][0],
            "input": ""
        }
        result.append(entry)
    conn.commit()
    conn.close()
    json_name = f'{outport_file_name}.json'
    with open(json_name, 'w', encoding='utf-8') as json_file:
        json.dump(result, json_file, ensure_ascii=False, indent=4)
    return '导出成功！'
        
def outport_at(indice, outport_file_name):
    result = []
    conn = sqlite3.connect('pufa-sqlite.db')
    cursor = conn.cursor()
    txt_name = f'{outport_file_name}.txt'
    with open(txt_name, 'w', encoding="utf-8") as file:
        for i in indice:
            cursor.execute('SELECT prompt_Ask FROM Prompt WHERE id =?', (i,))
            ask = cursor.fetchall()
            cursor.execute('SELECT prompt_Answer FROM Prompt WHERE id =?', (i,))
            answer = cursor.fetchall()
            if ask and answer:
                ask_text = ask[0][0]
                answer_text = answer[0][0]
                file.write(f'{ask_text}\n@@\n{answer_text}\n')
                if i != indice[-1]:
                    file.write('@@\n')
    return '导出成功！'

# 批量修改功能有关的函数
def search_knowledge(a):
    conn = sqlite3.connect('pufa-sqlite.db')
    cursor = conn.cursor()
    cursor.execute('SELECT id FROM Project WHERE Knowledge_Id =? ',(a,))
    resulta = cursor.fetchall()  
    a_values = [row[0] for row in resulta]
    conn.commit()
    conn.close()
    return(a_values)   

def search_cluster(b):
    conn = sqlite3.connect('pufa-sqlite.db')
    cursor = conn.cursor()
    cursor.execute('SELECT id FROM Project WHERE cluster_Id =? ',(b,))
    resultb = cursor.fetchall()  
    b_values = [row[0] for row in resultb]
    conn.commit()
    conn.close()    
    return(b_values)

def search(a,b):
    conn = sqlite3.connect('pufa-sqlite.db')
    cursor = conn.cursor()
    cursor.execute('SELECT id FROM Project WHERE Knowledge_Id =? ',(a,))
    resulta = cursor.fetchall()  
    a_values = [row[0] for row in resulta]
    cursor.execute('SELECT id FROM Project WHERE cluster_Id =? ',(b,))
    resultb = cursor.fetchall()  
    b_values = [row[0] for row in resultb]
    c_values = list(set(a_values) & set(b_values))
    conn.commit()
    conn.close()
    return(c_values)

def panduan(select_knowledge, select_cluster):
    knowledge_mapping = {'页面知识点': '1', '功能点': '2', '链': '3'}
    cluster_mapping = {'邮件相关': '1', '新建申请页面优化字段相关': '2', '同步数据相关': '3', '需求报表相关': '4'}
    if select_knowledge not in knowledge_mapping and select_cluster not in cluster_mapping:
        raise gr.Error("请至少选择一个选择问答对类型或问答对的簇")
    elif select_knowledge in knowledge_mapping and select_cluster not in cluster_mapping:
        a=knowledge_mapping[select_knowledge]
        return(search_knowledge(a))
    elif select_knowledge not in knowledge_mapping and select_cluster in cluster_mapping:
        b=cluster_mapping[select_cluster]
        return(search_cluster(b))
    else:
        a1=knowledge_mapping[select_knowledge]
        b1=cluster_mapping[select_cluster]
        return(search(a1,b1))
    
def add_prompt_Ask(p, add_text):
    conn = sqlite3.connect('pufa-sqlite.db')
    cursor = conn.cursor()
    for i in range(len(p)):
        cursor.execute('SELECT prompt_Ask FROM Prompt WHERE id =? ',(p[i],))
        result_ask = cursor.fetchall()
        if result_ask:
            prompt_Ask = result_ask[0]
            new_prompt_Ask = add_text+prompt_Ask[0]  # 构造新的prompt_Id值
            cursor.execute('UPDATE Prompt SET prompt_Ask = ? WHERE id = ?', (new_prompt_Ask, p[i]))
    conn.commit()
    conn.close()

def add_prompt_Answer(p,add_text):
    conn = sqlite3.connect('pufa-sqlite.db')
    cursor = conn.cursor()
    for i in range(len(p)):
        cursor.execute('SELECT prompt_Answer FROM Prompt WHERE id =? ',(p[i],))
        result_answer = cursor.fetchall()
        if result_answer:
            add_prompt_Answer = result_answer[0]
            new_prompt_Answer = add_text+add_prompt_Answer[0]  # 构造新的prompt_Id值
            cursor.execute('UPDATE Prompt SET prompt_Answer = ? WHERE id = ?', (new_prompt_Answer, p[i]))
    conn.commit()
    conn.close()

def panduan2(select_q_a,p,add_text):
    if select_q_a=="问题":
        add_prompt_Ask(p,add_text)
    elif select_q_a=="回答":
        add_prompt_Answer(p,add_text)
    else:
        raise gr.Error("请选择问题还是回答")
    return "修改完成"


# 历史问答对功能有关的函数
def import_history(txt_list):
    qa_dict = {}
    if txt_list is not None:
        for txt in txt_list:
            ask_list, answer_list = split_string_into_lists(txt)
            if len(ask_list) == len(answer_list):
                for ask, answer in zip(ask_list, answer_list):
                    qa_dict[ask] = answer
            else:
                gr.Error('上传的txt格式有问题，问题和回答对应不起来')
    conn = sqlite3.connect('pufa-sqlite.db')
    cursor = conn.cursor()
    cursor.execute('SELECT MAX(history_Id) FROM History')
    historyid = cursor.fetchone()[0]
    if historyid is None:
        historyid = 1
    else:
        historyid += 1
    for ask, answer in qa_dict.items():
        cursor.execute('INSERT INTO History (history_Ask, history_Answer, history_Id) VALUES (?, ?, ?)', (ask.strip(), answer.strip(), historyid))
        historyid += 1
    conn.commit()
    conn.close()
    return '批量导入成功！'

def single_imoprt_history(ask,answer):
    conn = sqlite3.connect('pufa-sqlite.db')
    cursor = conn.cursor() 
    cursor.execute('SELECT MAX(history_Id) FROM History')
    historyid = cursor.fetchone()[0]
    if historyid is None:
        historyid = 1
    else:
        historyid += 1
    if ask!=''and answer!='':
        cursor.execute('INSERT INTO History (history_Ask, history_Answer, history_Id) VALUES (?, ?, ?)', (ask.strip(), answer.strip(), historyid))
    else:
        raise gr.Error("请完整输入问题或回答")  
    conn.commit()
    conn.close()
    return '导入成功！'
        
def search_history(a):
    conn = sqlite3.connect('pufa-sqlite.db')
    cursor = conn.cursor()
    cursor.execute('SELECT history_Ask FROM History WHERE history_Id =? ',(a,))
    result_ask = cursor.fetchall()  
    cursor.execute('SELECT history_Answer FROM History WHERE history_Id =? ',(a,))
    result_answer = cursor.fetchall()
    conn.commit()
    conn.close()
    return(result_ask[0][0],result_answer[0][0])     

def modify_history(a,ask,answer):
    conn = sqlite3.connect('pufa-sqlite.db')
    cursor = conn.cursor()
    cursor.execute('UPDATE History SET history_Ask = ? WHERE history_Id = ?', (ask, a))
    cursor.execute('UPDATE History SET history_Answer = ? WHERE history_Id = ?', (answer, a))
    conn.commit()
    conn.close()
    return '保存修改成功！'

def outport_data_with_history(searched_result, search_history_outport_result_q, search_history_outport_result_a, history_id_outport, outport_json_history_name):
    result = []
    conn = sqlite3.connect('pufa-sqlite.db')
    cursor = conn.cursor()
    for i in searched_result:
        cursor.execute('SELECT prompt_Ask FROM Prompt WHERE id =?', (i,))
        ask = cursor.fetchall()
        cursor.execute('SELECT prompt_Answer FROM Prompt WHERE id =?', (i,))
        answer = cursor.fetchall()
        entry = {
            "historyID": history_id_outport,
            "front_content_ask": search_history_outport_result_q,
            "front_content_answer": search_history_outport_result_a,
            "instruction": ask[0][0],
            "output": answer[0][0],
            "input": ""
        }
        result.append(entry)
    conn.commit()
    conn.close()
    json_name = f'{outport_json_history_name}.json'
    with open(json_name, 'w', encoding='utf-8') as json_file:
        json.dump(result, json_file, ensure_ascii=False, indent=4)
    return '导出成功！'

# 模糊搜索历史问答对
def search_mo(information):
    conn = sqlite3.connect('pufa-sqlite.db')
    cursor = conn.cursor() 
    information = f'%{information}%'
    cursor.execute('SELECT history_Id, history_Ask, history_Answer FROM History WHERE history_Ask LIKE ?', (information,))
    result = cursor.fetchall()
    df = pd.DataFrame(result, columns=["history_Id", "history_Ask", "history_Answer"])
    conn.commit()
    conn.close()
    df['history_Ask'] = df['history_Ask'].apply(lambda x: x[:50] + '...' if len(x) > 50 else x)
    df['history_Answer'] = df['history_Answer'].apply(lambda x: x[:50] + '...' if len(x) > 50 else x)
    return df

# 历史df的select事件
def select_hsdf_id(evt: gr.SelectData, df):
    select_postion = evt.index
    hs_id = df.iloc[select_postion[0], 0]
    return hs_id

# group的select事件
def select_grpdf_id(evt: gr.SelectData, df, id_):
    select_postion = evt.index
    hs_id = df.iloc[select_postion[0], 0]
    id_.append(hs_id)
    unique_id = []
    [unique_id.append(x) for x in id_ if x not in unique_id]
    return unique_id

# 获得panduan的结果后，判断keyword以及展示数据
def process_what_searched(searched_result_json, group_keyword):
    conn = sqlite3.connect('pufa-sqlite.db')
    cursor = conn.cursor()
    searched_result_df = pd.DataFrame(columns=["group_Id", "group_Ask", "group_Answer"])
    for id_ in searched_result_json:
        cursor.execute('SELECT history_Id FROM Project WHERE id=?', (id_,))
        history_id = cursor.fetchall()
        # 如果要关闭historyid检测，则使用以下条件：
        # if history_id[0][0] == '天才':
        if history_id[0][0] is not None:
            pass
        else:
            cursor.execute('SELECT prompt_Id, prompt_Ask, prompt_Answer FROM Prompt WHERE id=?', (id_,))
            result = cursor.fetchall()
            if group_keyword != '':
                prompt_id = result[0][0]
                if prompt_id[-5:] == "00000":
                    group_id = prompt_id
                    group_ask = result[0][1]
                    group_answer = result[0][2]
                    if group_keyword in group_ask or group_keyword in group_answer:
                        entry = {
                            "group_Id": group_id,
                            "group_Ask": result[0][1],
                            "group_Answer": result[0][2]
                        }
                        searched_result_df = pd.concat([searched_result_df, pd.DataFrame([entry])], ignore_index=True)
            else:
                prompt_id = result[0][0]
                if prompt_id[-5:] == "00000":
                    group_id = prompt_id
                    entry = {
                        "group_Id": group_id,
                        "group_Ask": result[0][1],
                        "group_Answer": result[0][2]
                    }
                    searched_result_df = pd.concat([searched_result_df, pd.DataFrame([entry])], ignore_index=True)
    conn.commit()
    conn.close()
    searched_result_df['group_Ask'] = searched_result_df['group_Ask'].apply(lambda x: x[:50] + '...' if len(x) > 50 else x)
    searched_result_df['group_Answer'] = searched_result_df['group_Answer'].apply(lambda x: x[:50] + '...' if len(x) > 50 else x)
    return searched_result_df

def get_preview_basket_df(slcted_grp_id):
    conn = sqlite3.connect('pufa-sqlite.db')
    cursor = conn.cursor()
    basket = pd.DataFrame(columns=["group_Id", "group_Ask"])
    if slcted_grp_id != ['']:
        for id_ in slcted_grp_id:
            cursor.execute('SELECT prompt_Ask FROM Prompt WHERE prompt_Id=?', (id_,))
            result = cursor.fetchall()
            group_ask = result[0][0]
            entry = {
                "group_Id": id_,
                "group_Ask": group_ask
            }
            basket = pd.concat([basket, pd.DataFrame([entry])], ignore_index=True)
        conn.commit()
        conn.close()
        basket['group_Ask'] = basket['group_Ask'].apply(lambda x: x[:50] + '...' if len(x) > 50 else x)
    return basket

def return_empty_list():
    return []

def join_history_group(slcted_hs_id, slcted_grp_id, joined_json):
    conn = sqlite3.connect('pufa-sqlite.db')
    cursor = conn.cursor()
    
    for i in slcted_grp_id:
        cursor.execute('SELECT prompt_Id FROM Project WHERE group_Id =?', (i,))
        group_qas = cursor.fetchall()
        
        cursor.execute('SELECT history_Ask, history_Answer FROM History WHERE id =?', (slcted_hs_id,))
        history_qa = cursor.fetchall()
        history_ask = history_qa[0][0]
        history_answer = history_qa[0][1]
        history_part = []
        history_part.append([history_ask, history_answer])
        
        for group_qa in group_qas:
            prompt_id = group_qa[0]
            cursor.execute('SELECT prompt_Ask, prompt_Answer FROM Prompt WHERE prompt_Id =?', (prompt_id,))
            prompt_qa = cursor.fetchall()
            prompt_ask = prompt_qa[0][0]
            prompt_answer = prompt_qa[0][1]
            
            entry = {
                "history": history_part,
                "instruction": prompt_ask,
                "output": prompt_answer,
                "input": ""
            }
            joined_json.append(entry)
        
    conn.commit()
    conn.close()
    return joined_json

def update_id_df(slcted_hs_id, slcted_grp_id, search_history_outport_result_df, searched_result_df, joined_json):
    if joined_json == []:
        pass
    else:
        conn = sqlite3.connect('pufa-sqlite.db')
        cursor = conn.cursor()
        search_history_outport_result_df = search_history_outport_result_df[search_history_outport_result_df['history_Id'] != int(slcted_hs_id)]

        for grp_id in slcted_grp_id:
            searched_result_df = searched_result_df[searched_result_df['group_Id'] != grp_id]
            cursor.execute("UPDATE Project SET history_Id = ? WHERE group_Id = ?", (slcted_hs_id, grp_id))

        slcted_hs_id = ''
        slcted_grp_id = []
        conn.commit()
        conn.close()
    return slcted_hs_id, slcted_grp_id, search_history_outport_result_df, searched_result_df

def outport_joined_data(joined_json, outport_json_history_name):
    json_name = f'{outport_json_history_name}.json'
    with open(json_name, 'w', encoding='utf-8') as json_file:
        json.dump(joined_json, json_file, ensure_ascii=False, indent=4)
    return '导出成功！', []

def select_all_group(df):
    all_group_json = df['group_Id'].values
    all_group_json = list(all_group_json)
    return all_group_json

# with gr.Blocks(css='./llm2.css') as llmqa_face:
# with gr.Blocks(theme=gr.themes.Base(primary_hue='orange', secondary_hue='orange')) as llmqa_face:
with gr.Blocks(theme='NoCrypt/miku', css='./llm2.css') as llmqa_face:
    gr.Markdown('# 溜溜梅问答对管理\nLLM QA Manager')
    
    
    # 导入功能
    with gr.Tab('导入'):
        # 前端
        gr.Markdown('## 开始导入')
        with gr.Row():
            with gr.Column():
                select_project = gr.Dropdown(label='选择项目', choices=["浦发"], value='浦发')
                select_knowledge = gr.Dropdown(label='选择问答对类型', choices=["页面知识点", "功能点", "链"])
                select_cluster = gr.Dropdown(label='选择问答对的簇', choices=["邮件相关", "新建申请页面优化字段相关", "同步数据相关", "需求报表相关"])
            with gr.Column():
                with gr.Tab('导入原始问答对'):
                    upload_file = gr.File(file_count='multiple', label='请拖入或上传一个或多个.txt文件，保证格式正确')
                    upload_button = gr.Button(value='点击导入原始问答对')
                    upload_s_or_f = gr.Textbox(label='导入成功了吗？')
                    txt_list = gr.JSON(visible=False)
                    preview_json = gr.JSON(visible=True, value=[])
                    preview_text = gr.Textbox(label='预览')
                with gr.Tab('导入扩写问答对'):
                    gr.Markdown('导入扩写问答对时，无需在左侧做选择~')
                    upload_kuo_file = gr.File(file_count='multiple', label='请拖入或上传一个或多个.txt文件，保证格式正确')
                    add_prompt_id_button = gr.Button(value='点击导入前，先为扩写问答对赋予id')
                    upload_kuo_button = gr.Button(value='点击导入扩写问答对', elem_classes='button2')
                    upload_kuo_s_or_f = gr.Textbox(label='导入成功了吗？')
                    json_kuo_list = gr.JSON(label='预览', visible=True)
                    preview_kuo_text = gr.Textbox(label='预览', visible=False)
        gr.Markdown('## 新增...')
        # 后端
        upload_file.change(fn=read_txts, inputs=upload_file, outputs=txt_list)
        txt_list.change(fn=preprocess_txts, inputs=txt_list, outputs=preview_json)
        preview_json.change(fn=preview_in_textbox, inputs=preview_json, outputs=preview_text)
        upload_button.click(
            fn=daoru_function, 
            inputs=[select_project, select_knowledge, select_cluster, preview_json],
            outputs=upload_s_or_f
        )
        upload_kuo_file.change(fn=read_jsons, inputs=upload_kuo_file, outputs=[preview_kuo_text, json_kuo_list])
        add_prompt_id_button.click(fn=add_prompt_id, inputs=[upload_kuo_file], outputs=json_kuo_list)
        upload_kuo_button.click(fn=kuo_function, inputs=[select_project, select_knowledge, select_cluster, json_kuo_list], outputs=upload_kuo_s_or_f)

    
    # 扩写功能
    with gr.Tab('扩写'):
        # 前端
        gr.Markdown('## 选择ID进行扩写或批量扩写')
        chatgpt_state = gr.Textbox(label='gpt的运行状况')
        with gr.Row():
            with gr.Tab('单个扩写'):
                with gr.Row():
                    with gr.Column():
                        kuo_prompt_id = gr.Textbox(label='输入要扩写的promptID')
                        kuo_searched_ask = gr.Textbox(label='根据ID查询到的问题')
                        kuo_searched_answer = gr.Textbox(label='根据ID查询到的回答')
                    with gr.Column():
                        kuo_system_msg = gr.Textbox(label='修改问题前缀', lines=3, value='请重写以下问句成5种版本，要求将问句信息全部考虑在内：')
                        kuo_gptoutput = gr.Textbox(label='实时预览gpt的输出')
                        start_kuo_button = gr.Button(value='开始扩写')
                        kuo_json_name = gr.Textbox(label='设置导出的json文件名称，不需要写.json', value='扩写结果')
                        kuo_outport_button = gr.Button(value='导出')
                        kuo_outport_s_or_f = gr.Textbox(label='导出成功了吗？')
            with gr.Tab('批量扩写'):
                with gr.Row():
                    with gr.Column():
                        select_project = gr.Dropdown(label='选择项目', choices=["浦发"])
                        select_knowledge = gr.Dropdown(label='选择问答对类型', choices=["页面知识点", "功能点", "链"])
                        select_cluster = gr.Dropdown(label='选择问答对的簇', choices=["邮件相关", "新建申请页面优化字段相关", "同步数据相关", "需求报表相关"])
                        pkuo_search_button = gr.Button(value='查询未扩写过的id')
                        pkuo_search_ids = gr.JSON(label='根据条件查询到的ID')
                    with gr.Column():
                        pkuo_system_msg = gr.Textbox(label='修改问题前缀', lines=3, value='请重写以下问句成5种版本，要求将问句信息全部考虑在内：', interactive=True)
                        pkuo_gptoutput = gr.Textbox(label='实时预览gpt的输出')
                        pkuo_start_button = gr.Button(value='开始批量扩写')
                        
                        now_process_prompt_id = gr.Number(label='目前正在处理的index', value=-1, precision=0)
                        output_done_signiture = gr.Number(value=0, precision=0)
                        pkuo_stop_button = gr.Button(value='强制停止，停止后需要刷新页面')
                        pkuo_json_name = gr.Textbox(label='设置导出的json文件名称，不需要写.json', value='扩写结果')
                        pkuo_outport_button = gr.Button(value='导出')
                        pkuo_outport_s_or_f = gr.Textbox(label='导出成功了吗？')
                        pkuo_result = gr.JSON(value=[])       
        #后端
        kuo_prompt_id.change(fn=search_id, inputs=kuo_prompt_id, outputs=[kuo_searched_ask, kuo_searched_answer])                
        start_kuo_button.click(fn=get_completion, inputs=[kuo_searched_ask, kuo_system_msg], outputs=kuo_gptoutput)
        kuo_outport_button.click(fn=outport, inputs=[kuo_prompt_id, kuo_searched_answer, kuo_gptoutput, kuo_json_name], outputs=kuo_outport_s_or_f)
        kuo_outport_s_or_f.change(fn=process_kuo_json, inputs=kuo_outport_s_or_f)
        
        pkuo_search_button.click(fn=panduan_promax, inputs=[select_knowledge, select_cluster], outputs=pkuo_search_ids)
        pkuo_start_button.click(fn=update_index, inputs=[now_process_prompt_id, pkuo_search_ids], outputs=now_process_prompt_id)
        now_process_prompt_id.change(fn=pkuo, inputs=[now_process_prompt_id, pkuo_system_msg, pkuo_search_ids, pkuo_gptoutput], outputs=pkuo_gptoutput)
        pkuo_gptoutput.change(fn=index_addone, inputs=output_done_signiture, outputs=output_done_signiture)
        output_done_signiture.change(fn=display_result, inputs=[now_process_prompt_id, pkuo_search_ids, pkuo_gptoutput, pkuo_result], outputs=pkuo_result)
        output_done_signiture.change(fn=update_index, inputs=[now_process_prompt_id, pkuo_search_ids], outputs=now_process_prompt_id)
        pkuo_stop_button.click(fn=stop_it, outputs=[output_done_signiture, now_process_prompt_id])
        pkuo_outport_button.click(fn=pkuo_outport, inputs=[pkuo_result, pkuo_json_name], outputs=pkuo_outport_s_or_f)
        pkuo_outport_s_or_f.change(fn=process_kuo_json, inputs=pkuo_outport_s_or_f)
    
    
    # 批量修改功能
    with gr.Tab('批量修改'):
        # 前端
        gr.Markdown('## 查询ID批量修改问答对内容')
        with gr.Row():
            with gr.Column():
                select_project = gr.Dropdown(label='选择项目', choices=["浦发"], value='浦发')
                select_knowledge = gr.Dropdown(label='选择问答对类型', choices=["页面知识点", "功能点", "链"])
                select_cluster = gr.Dropdown(label='选择问答对的簇', choices=["邮件相关", "新建申请页面优化字段相关", "同步数据相关", "需求报表相关"])
                modify_search_button = gr.Button(value='查询')
                searched_result = gr.JSON(visible=True, label='根据条件查询到的ID')
    
                knowledge_mapping = {'页面知识点': '1', '功能点': '2', '链': '3'}
                cluster_mapping = {'邮件相关': '1', '新建申请页面优化字段相关': '2', '同步数据相关': '3', '需求报表相关': '4'}
            with gr.Column():
                select_q_a = gr.Dropdown(label='选择修改问题还是回答', choices=["问题", "回答"])
                add_text = gr.Textbox(label='写入要增加的内容')
                modify_button = gr.Button(value='点击统一修改')
                modified_data = gr.Textbox(label='修改成功了吗？')
        # 后端
        modify_search_button.click(fn=panduan, inputs=[select_knowledge, select_cluster], outputs=searched_result)
        modify_button.click(fn=panduan2, inputs=[select_q_a, searched_result, add_text], outputs=modified_data)
    
    
    # 历史问答对功能
    with gr.Tab('历史问答对'):
        gr.Markdown('## 配置历史问答对')
        gr.Markdown('### 导入历史问答对')
        with gr.Row():
            with gr.Tab('导入'):
                history_ask = gr.Textbox(label='历史问题')
                history_answer = gr.Textbox(label='历史回答')
                input_history_button1 = gr.Button(value='导入')
                one_import_s_or_f = gr.Textbox(label='导入成功了吗？')
            with gr.Tab('批量导入'):
                history_qa_file = gr.File(label='请拖入或上传一个写有历史问答对的.txt文件，保证格式正确', file_count='multiple')
                input_history_button2 = gr.Button(value='批量导入')
                pimport_s_or_f = gr.Textbox(label='批量导入成功了吗？')
                txt_list_json = gr.JSON(visible=True)
        gr.Markdown('### 查询历史问答对')
        with gr.Row():
            with gr.Column():
                history_id = gr.Textbox(label='输入想查询的historyID')
                search_history_button = gr.Button(value='查询')
                history_id_q_content = gr.Textbox(label='查询到的历史问题，可以修改')
                history_id_a_content = gr.Textbox(label='查询到的历史回答，可以修改')
            with gr.Column():
                history_id_list = gr.Textbox(label='historyID密码本', lines=5, value='1: 邮件相关的\n2: 同步数据相关的\n3: 新建申请页面字段优化相关的\n4: 需求报表相关的\n5: 新建页面相关的\n6: 系统管理菜单相关的\n7: 修复bug相关的')
        save_modify_button = gr.Button(value='保存')
        save_modify_s_or_f = gr.Textbox(label='保存修改成功了吗？')
        gr.Markdown('### 导出带有历史的问答对')
        with gr.Row():
            with gr.Column():
                select_project = gr.Dropdown(label='选择项目', choices=["浦发"], value='浦发')
                select_knowledge = gr.Dropdown(label='选择问答对类型', choices=["页面知识点", "功能点", "链"])
                select_cluster = gr.Dropdown(label='选择问答对的簇', choices=["邮件相关", "新建申请页面优化字段相关", "同步数据相关", "需求报表相关"])
                history_search_prompt_button = gr.Button(value='查询')
                searched_result = gr.JSON(visible=True, label='根据条件查询到的ID')
            with gr.Column():
                history_id_outport = gr.Textbox(label='输入想查询的historyID')
                search_history_outport_button = gr.Button(value='查询')
                search_history_outport_result_q = gr.Textbox(label='查询到的历史问题')
                search_history_outport_result_a = gr.Textbox(label='查询到的历史回答')
        outport_json_history_name = gr.Textbox(label='设置导出的json文件名称，不需要写.json', value='有历史的问答对')
        outport_history = gr.Button(value='点击导出带有历史的问答对')
        outport_history_s_or_f = gr.Textbox(label='导出成功了吗？')
        #后端
        input_history_button1.click(fn=single_imoprt_history, inputs=[history_ask, history_answer], outputs=[one_import_s_or_f])
        history_qa_file.change(fn=read_txts, inputs=[history_qa_file], outputs=[txt_list_json])
        
        input_history_button2.click(fn=import_history, inputs=[txt_list_json], outputs=[pimport_s_or_f])
        
        save_modify_button.click(fn=modify_history, inputs=[history_id,history_id_q_content,history_id_a_content], outputs=[save_modify_s_or_f])
        search_history_button.click(fn=search_history, inputs=[history_id], outputs=[history_id_q_content,history_id_a_content])
        
        history_search_prompt_button.click(fn=panduan, inputs=[select_knowledge, select_cluster], outputs=searched_result)
        search_history_outport_button.click(fn=search_history, inputs=[history_id_outport], outputs=[search_history_outport_result_q, search_history_outport_result_a])
        outport_history.click(fn=outport_data_with_history, inputs=[searched_result, search_history_outport_result_q, search_history_outport_result_a, history_id_outport, outport_json_history_name], outputs=outport_history_s_or_f)
        
        
    # 导出功能
    with gr.Tab('导出'):
        # 前端
        gr.Markdown('## 导出不带历史的问答对')
        with gr.Row():
            with gr.Column():
                select_project = gr.Dropdown(label='选择项目', choices=["浦发"], value='浦发')
                select_knowledge = gr.Dropdown(label='选择问答对类型', choices=["页面知识点", "功能点", "链"])
                select_cluster = gr.Dropdown(label='选择问答对的簇', choices=["邮件相关", "新建申请页面优化字段相关", "同步数据相关", "需求报表相关"])
                knowledge_mapping = {'页面知识点': '1', '功能点': '2', '链': '3'}
                cluster_mapping = {'邮件相关': '1', '新建申请页面优化字段相关': '2', '同步数据相关': '3', '需求报表相关': '4'}
                outport_search_button = gr.Button(value='查询')
                searched_result = gr.JSON(visible=True, label='根据条件查询到的ID')
            with gr.Column():
                outport_file_name = gr.Textbox(label='设置导出的文件名称，不需要写.json或.txt', value='导出结果')
                outport_button = gr.Button(value='点击导出json格式')
                outport_at_button = gr.Button(value='点击导出@@格式')
                success_fail_text = gr.Textbox(label='导出成功了吗？')
        gr.Markdown('## 导出带历史的问答对')
        with gr.Row():
            with gr.Column(scale=4):
                with gr.Row():
                    with gr.Column():
                        history_info = gr.Textbox(label='输入关键词搜索相关history')
                        search_history_outport_button = gr.Button(value='搜索')
                        search_history_outport_result_df = gr.DataFrame(label='搜索到的历史问答对', value=pd.DataFrame({"history_Id": [],"history_Ask": [],"history_Answer": []}), wrap=True, interactive=False)

                    with gr.Column():
                        with gr.Row():
                            hselect_project = gr.Dropdown(label='选择项目', choices=["浦发"], value='浦发')
                            hselect_knowledge = gr.Dropdown(label='选择问答对类型', choices=["页面知识点", "功能点", "链"])
                            hselect_cluster = gr.Dropdown(label='选择问答对的簇', choices=["邮件相关", "新建申请页面优化字段相关", "同步数据相关", "需求报表相关"])

                        group_keyword = gr.Textbox(label='输入关键词搜索相关group')
                        history_search_prompt_button = gr.Button(value='搜索')
                        select_all_group_button = gr.Button(value='全选group')
                        searched_result_json = gr.JSON(visible=False)
                        searched_result_df = gr.DataFrame(label='根据条件查询到的group', value=pd.DataFrame({"group_Id": [],"group_Ask": [],"group_Answer": []}), wrap=True, interactive=False)

                with gr.Row():
                    with gr.Column():
                        outport_json_history_name = gr.Textbox(label='设置导出的json文件名称，不需要写.json', value='有历史的问答对')
                        outport_history = gr.Button(value='点击导出带有历史的问答对')
                        outport_history_s_or_f = gr.Textbox(label='导出成功了吗？')

            with gr.Column(scale=1):
                slcted_hs_id = gr.Textbox(label='选中的historyID')
                slcted_grp_id = gr.JSON(label='选中的groupID', visible=False, value=[])
                slcted_grp_basket = gr.DataFrame(label='选中的group篮子', value=pd.DataFrame({"group_Id": [],"group_Ask": []}), wrap=True)
                clear_group_basket_button = gr.Button(value='清除所选groupID')
                join_button = gr.Button(value='确定拼接')
                joined_json = gr.JSON(label='预览拼接好的内容', value=[])
        #后端
        outport_search_button.click(fn=panduan, inputs=[select_knowledge, select_cluster], outputs=searched_result)
        outport_button.click(fn=outport_func, inputs=[searched_result, outport_file_name], outputs=success_fail_text)
        outport_at_button.click(fn=outport_at, inputs=[searched_result, outport_file_name], outputs=success_fail_text)
     
        search_history_outport_button.click(fn=search_mo, inputs=history_info, outputs=search_history_outport_result_df)
        # 选中历史df返回id
        search_history_outport_result_df.select(fn=select_hsdf_id, inputs=search_history_outport_result_df, outputs=slcted_hs_id)

        # 根据三个条件来搜索，返回id到隐藏json
        history_search_prompt_button.click(fn=panduan, inputs=[hselect_knowledge, hselect_cluster], outputs=searched_result_json)
        # 接受隐藏json，展示符合条件的数据
        searched_result_json.change(fn=process_what_searched, inputs=[searched_result_json, group_keyword], outputs=searched_result_df)
        # 全选group按钮
        select_all_group_button.click(fn=select_all_group, inputs=searched_result_df, outputs=slcted_grp_id)
        # 选中group的df返回id
        searched_result_df.select(fn=select_grpdf_id, inputs=[searched_result_df, slcted_grp_id], outputs=slcted_grp_id)
        # 隐藏json变化后，preview的df同步变化
        slcted_grp_id.change(fn=get_preview_basket_df, inputs=slcted_grp_id, outputs=slcted_grp_basket)
        # 按按钮清除篮子
        clear_group_basket_button.click(fn=return_empty_list, outputs=slcted_grp_id)
        # 确认拼接
        join_button.click(fn=join_history_group, inputs=[slcted_hs_id, slcted_grp_id, joined_json], outputs=joined_json)
        # 拼接完成后，清除两个id，更新两个df
        joined_json.change(fn=update_id_df, inputs=[slcted_hs_id, slcted_grp_id, search_history_outport_result_df, searched_result_df, joined_json], outputs=[slcted_hs_id, slcted_grp_id, search_history_outport_result_df, searched_result_df])
        # 导出
        outport_history.click(fn=outport_joined_data, inputs=[joined_json, outport_json_history_name], outputs=[outport_history_s_or_f, joined_json])

        
llmqa_face.queue()
llmqa_face.launch()