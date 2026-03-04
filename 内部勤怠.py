import sqlite3
import datetime 
import streamlit as st
import pandas as pd
from dateutil.relativedelta import relativedelta
from datetime import *
#from PIL import Image 

#st.set_page_config(layout="wide")

def sum_overtime():

    # データベース接続
    conn = sqlite3.connect("hokko.db")
    c = conn.cursor()

    # 対象となる月を指定
    
    sdate_year = due_date.year
    sdate_month =due_date.month

    if sdate_month==12:
        edate_month = 1
        edate_year = sdate_year + 1
    else:
        edate_month = sdate_month + 1
        edate_year=sdate_year

    edate = date(edate_year,edate_month,20)
    edate_str = str(edate)

    query = """
        select sdatetime,edatetime,残業時間 from attendanceT 
        where date >= ? and date <= ? and member = ?
    """

    df = pd.read_sql_query(query,conn,params=[from_due_date,to_due_date,staff])
    # Streamlitを使用してデータフレームと合計を表示
    st.dataframe(df, width='stretch',height=800,hide_index=True)

    conn.close()

    
def all_overtime():
    sdate_year = due_date.year
    sdate_month =due_date.month

    if sdate_month==12:
        edate_month = 1
        edate_year = sdate_year + 1
    else:
        edate_month = sdate_month + 1
        edate_year=sdate_year

    edate = date(edate_year,edate_month,20)
    edate_str =edate.strftime("%Y-%m-%d")

    conn = sqlite3.connect('hokko.db')

    query = """
        select * from attendanceT 
        where date >= ? and date <= ? and member = ?
    """

    df = pd.read_sql_query(query,conn,params=[from_due_date,to_due_date,staff])
    
    df['残業時間'] = pd.to_timedelta(df['残業時間'])
    df['深夜残業'] = pd.to_timedelta(df['深夜残業'])
    #df['深夜手当'] = pd.to_timedelta(df['深夜手当'])

    result = df.groupby('member').agg({'残業時間':'sum','深夜残業':'sum'})

    result['残業時間'] = result['残業時間'].dt.total_seconds() // 3600 + (result['残業時間'].dt.total_seconds() % 3600)/3600
    result['深夜残業'] = result['深夜残業'].dt.total_seconds() // 3600 + (result['深夜残業'].dt.total_seconds() % 3600)/3600
    #result['深夜手当'] = result['深夜手当'].dt.total_seconds() // 3600 + (result['深夜手当'].dt.total_seconds() % 3600)/3600

    st.dataframe(result,hide_index=True,width='content')

    conn.close()

def create_datetime(due_date,start_time,end_time):

    after5 = timedelta(0)
    before22 = timedelta(0)
    n_overtime = timedelta(0)
    midnight_overtime = timedelta(0)
    midnight_treat = timedelta(0)

    # 開始日時と終了日時を作成
    start_datetime = datetime.combine(due_date,start_time)
    end_datetime = datetime.combine(due_date,end_time)

    if end_datetime < start_datetime:
        end_datetime = end_datetime + timedelta(days=1)

    midnight_slevel = datetime.combine(due_date,time(22,0))
    midnight_elevel = datetime.combine(due_date,time(5,0))+ timedelta(days=1)

    # 休憩時間を考慮した労働時間を計算
    if end_datetime - start_datetime > timedelta(hours=5):
        if midnight_slevel - start_datetime >= timedelta(hours=5):
            rest_time = timedelta(hours=1)
            rest_time_midnight = timedelta(0)
        else:
            rest_time = timedelta(0)
            rest_time_midnight = timedelta(hours=1)

    else:
        rest_time = timedelta(0)
        rest_time_midnight = timedelta(0)

    work_time = (end_datetime - start_datetime) - rest_time - rest_time_midnight

    # 残業時間を計算
    overtime = max(work_time - timedelta(hours=8), timedelta(0))

    if end_datetime > midnight_slevel:

        if end_datetime > midnight_elevel:
            end_midnight_datetime = midnight_elevel
        else:
            end_midnight_datetime = end_datetime

        if start_datetime < midnight_slevel:
            start_midnight_datetime = midnight_slevel
        else:
            start_midnight_datetime = start_datetime

        after5 = max(end_datetime - end_midnight_datetime,timedelta(0))
        before22 = max(midnight_slevel - start_datetime - timedelta(hours=9) , timedelta(0))
        midnight_overtime = max(overtime - after5 - before22,timedelta(0))
        midnight_treat = max(end_midnight_datetime - start_midnight_datetime - rest_time_midnight - midnight_overtime,timedelta(0))
    
    n_overtime = overtime - midnight_overtime

    # 開始日時をSQLite3テーブルに登録できる書式に変換
    start_datetime_str = start_datetime.strftime('%Y-%m-%d %H:%M')
    end_datetime_str = end_datetime.strftime('%Y-%m-%d %H:%M')

    # 労働時間と残業時間をSQLite3に登録できる書式に変換
    work_time_str = str(work_time)
    n_overtime_str = str(n_overtime)
    midnight_treat_str = str(midnight_treat)
    midnight_overtime_str = str(midnight_overtime)
    
    return start_datetime_str,end_datetime_str,work_time_str,n_overtime_str,midnight_overtime_str,midnight_treat_str

# DB に接続（なければ自動で作成される）
conn = sqlite3.connect("voice_record.db")
cur = conn.cursor()

# テーブルが存在しなければ作成
cur.execute("""
CREATE TABLE IF NOT EXISTS attendanceT (
    member TEXT,
    date TEXT,
    sdatetime TEXT,
    edatetime TEXT,
    al_morning TEXT,
    alc_afternoon TEXT,
    労働時間 TEXT,
    残業時間 TEXT,
    深夜残業 TEXT,
    深夜手当 TEXT
)
""")

conn.close()


conn = sqlite3.connect('hokko.db')

due_date = st.date_input('登録日')
due_date_year = due_date.year
due_date_month = due_date.month
from_due_date = date(due_date.year,due_date.month,21)

due_date_str = due_date.strftime("%Y-%m-%d")

if due_date.day <= 20:
    from_due_date = from_due_date - relativedelta(months=1)

to_due_date = from_due_date + relativedelta(months=1) - relativedelta(days=1)

member = ['寺田明美','中川恭子','下田葵','松本雅志']

conn.close()

staff = st.radio('氏名',member,horizontal=True)

start_time = st.time_input('開始時間',time(7,40))
                    
end_time = st.time_input('終了時間',step=300)

if st.button('勤怠登録'):

    a1,a2,a3,a4,a5,a6 = create_datetime(due_date,start_time,end_time)

    start_time = str(start_time)
    end_time = str(end_time)

    alc = 0

    conn = sqlite3.connect('hokko.db')
    c = conn.cursor()

    c.execute('select * from attendanceT where member=? and date=?',(staff,due_date_str,))
    row = c.fetchone()

    if row:
        c.execute('update attendanceT set sdatetime=?,edatetime=?,労働時間=?,残業時間=?,深夜残業=?,深夜手当=?,alc_morning=?,alc_afternoon=? where member=? and date=?',(a1,a2,a3,a4,a5,a6,alc,alc,staff,due_date_str,))
        conn.commit()    
    else:
        c.execute(f"INSERT INTO attendanceT (member,sdatetime,edatetime,労働時間,残業時間,深夜残業,深夜手当,date,alc_morning,alc_afternoon) VALUES (?,?,?,?,?,?,?,?,?,?)",
                (staff,a1,a2,a3,a4,a5,a6,due_date_str,alc,alc))
        conn.commit()
    conn.close()

all_overtime()

st.divider()

if st.button('削除'):
    conn = sqlite3.connect('hokko.db')
    c = conn.cursor()
    c.execute('delete from  attendanceT where member=? and date=?',(staff,due_date_str,))
    conn.commit()
    conn.close()

sum_overtime()
