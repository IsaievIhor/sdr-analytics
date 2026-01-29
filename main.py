import streamlit as st
import pandas as pd
import plotly.express as px
from urllib.parse import quote

# 1. Налаштування сторінки
st.set_page_config(page_title="SDR Analytics", layout="wide")

# 2. Підключення до Google Sheets
sheet_id = "1t81gGgPDacVxR4kJ_s9seXi94Y4CIMh5b9_3vlYkqC4"
sheet_name = "база угод"
encoded_name = quote(sheet_name)
url = f"https://docs.google.com/spreadsheets/d/{sheet_id}/gviz/tq?tqx=out:csv&sheet={encoded_name}"

@st.cache_data
def load_data():
    data = pd.read_csv(url)
    data['AQL date'] = pd.to_datetime(data['AQL date'])
    # Залишаємо тільки логіку Win Rate
    data['Is_Won'] = data['Stage'].apply(lambda x: 1 if x == 'Closed Won' else (0 if x == 'Closed Lost' else None))
    return data

df = load_data()


# 3. Фільтри у бічній панелі
st.sidebar.header("Фільтри")

# Фільтр по країнах
all_countries = st.sidebar.checkbox("Вибрати всі країни", value=True)
if all_countries:
    selected_countries = df['Client country'].unique().tolist()
else:
    selected_countries = st.sidebar.multiselect("Країна", options=df['Client country'].unique(), default=[])

# Фільтр по CRM
all_crms = st.sidebar.checkbox("Вибрати всі CRM", value=True)
if all_crms:
    selected_crms = df['Client CRM'].unique().tolist()
else:
    selected_crms = st.sidebar.multiselect("CRM", options=df['Client CRM'].unique(), default=[])

# Фільтр по датах
min_date = df['AQL date'].min().date()
max_date = df['AQL date'].max().date()
date_range = st.sidebar.date_input("Період", [min_date, max_date])

# Застосування фільтрів
filtered_df = df[
    (df['Client country'].isin(selected_countries)) & 
    (df['Client CRM'].isin(selected_crms)) &
    (df['AQL date'].dt.date >= date_range[0]) &
    (df['AQL date'].dt.date <= date_range[1])
]

st.divider()
    
# 4. Візуалізація
st.title("📊 SDR Analytics Dashboard")

col1, col2 = st.columns(2)

with col1:
    st.subheader("Win Rate за країнами")
    
    # 1. Створюємо агреговану таблицю: рахуємо середнє (Win Rate) та кількість (Total Deals)
    country_stats = filtered_df.dropna(subset=['Is_Won']).groupby('Client country').agg(
        win_rate=('Is_Won', lambda x: x.mean() * 100),
        total_deals=('Is_Won', 'count')
    ).reset_index()

    # 2. Будуємо графік, додаючи total_deals у custom_data
    fig_country = px.bar(
        country_stats, 
        x='Client country', 
        y='win_rate', 
        labels={'win_rate': 'Win Rate (%)', 'total_deals': 'Кількість угод'},
        text_auto='.1f', 
        color='Client country',
        # Додаємо кількість угод у спливаюче вікно
        hover_data={'win_rate': ':.1f', 'total_deals': True}
    )

    # Оновлюємо вигляд підказки для кращого читання
    fig_country.update_traces(
        hovertemplate="<b>%{x}</b><br>Win Rate: %{y:.1f}%<br>Всього угод: %{customdata[0]}"
    )

    st.plotly_chart(fig_country, use_container_width=True)

with col2:
    st.subheader("Win Rate за CRM")
    wr_crm = filtered_df.dropna(subset=['Is_Won']).groupby('Client CRM')['Is_Won'].mean() * 100
    fig_crm = px.bar(wr_crm.reset_index(), x='Client CRM', y='Is_Won', labels={'Is_Won':'Win Rate (%)'}, text_auto='.1f', color='Client CRM')
    st.plotly_chart(fig_crm, use_container_width=True)

st.divider()

col3, col4 = st.columns(2)

with col3:
    st.subheader("Розподіл угод за стадіями (Stage)")
    stage_counts = filtered_df['Stage'].value_counts().reset_index()
    fig_stage = px.pie(stage_counts, names='Stage', values='count', hole=0.4)
    st.plotly_chart(fig_stage, use_container_width=True)

with col4:
    st.subheader("Кількість угод за джерелом (Source)")
    source_counts = filtered_df['Source'].value_counts().reset_index()
    fig_source = px.bar(source_counts, x='Source', y='count', color='Source')
    st.plotly_chart(fig_source, use_container_width=True)

    st.divider()

# Групуємо дані по бюджету та рахуємо середній Win Rate для кожного рівня витрат    
st.divider()
st.subheader("📊 Ефективність та об'єм за категоріями бюджету")

# 1. Рахуємо Win Rate ТА кількість угод одночасно
budget_stats = filtered_df.groupby('PPC budget USD').agg(
    Win_Rate=('Is_Won', 'mean'),
    Deals_Count=('Is_Won', 'count')
).reset_index()

budget_stats['Win Rate (%)'] = budget_stats['Win_Rate'] * 100

# 2. Порядок категорій
budget_order = ["0", "0-500", "500-1000", "1000-2000", "2000-5000", "5000-10000", "10000-20000", "20000+"]

# 3. Побудова графіка
fig_budget = px.bar(
    budget_stats, 
    x='PPC budget USD', 
    y='Win Rate (%)',
    # Додаємо Deals_Count у дані, щоб Plotly його бачив
    custom_data=['Deals_Count'],
    text_auto='.1f',
    color='PPC budget USD',
    title="Який сегмент бюджету має найкращу конверсію? (з кількістю угод)",
    labels={'PPC budget USD': 'Діапазон бюджету', 'Win Rate (%)': 'Win Rate (%)'},
    category_orders={"PPC budget USD": budget_order}
)

# 4. Налаштування підказки (Tooltip)
fig_budget.update_traces(
    hovertemplate="<br>".join([
        "Бюджет: %{x}",
        "Win Rate: %{y:.1f}%",
        "Кількість угод: %{customdata[0]}" # Виводимо кількість угод
    ])
)

fig_budget.update_xaxes(type='category')
fig_budget.update_layout(showlegend=False)

st.plotly_chart(fig_budget, use_container_width=True)
st.divider()

# Групуємо дані, щоб побачити ймовірність успіху залежно від тривалості
prob_df = temp_df[temp_df['cycle_days'] >= 0].groupby('cycle_days')['Is_Won'].mean().reset_index()

fig_trend = px.line(prob_df, x='cycle_days', y='Is_Won', 
                    title='Ймовірність закриття угоди від її тривалості',
                    labels={'cycle_days': 'Тривалість угоди (дні)', 'Is_Won': 'Шанс на перемогу (%)'})

# Додаємо "червону лінію" на 19 днях
fig_trend.add_vline(x=19, line_dash="dash", line_color="red", annotation_text="Зона ризику (19 днів)")

st.plotly_chart(fig_trend)
st.divider()

# 5. Таблиця даних (опціонально)
with st.expander("Переглянути сирі дані"):
    st.write(filtered_df)


st.subheader("⚠️ Data Issues (Помилки в даних)")

# --- 1. ПІДГОТОВКА ПЕРЕВІРОК (Логічні фільтри) ---

# Відсутня Closing Date для закритих угод
missing_closing_date = filtered_df[
    (filtered_df['Stage'].isin(['Closed Won', 'Closed Lost'])) & 
    (filtered_df['Closing Date'].isna())
]

# Пуста або занадто коротка причина програшу (менше 5 символів)
invalid_loss_reason = filtered_df[
    (filtered_df['Stage'] == 'Closed Lost') & 
    ((filtered_df['Loss reason description'].isna()) | (filtered_df['Loss reason description'].astype(str).str.len() < 5))
]

# Аномалія: Виграно з бюджетом 0
zero_budget_won = filtered_df[
    (filtered_df['Stage'] == 'Closed Won') & 
    (filtered_df['PPC budget USD'].isin(['0', 0, '0-0']))
]

# Помилка: Виграно без вказаного періоду підписки
missing_subscription = filtered_df[
    (filtered_df['Stage'] == 'Closed Won') & 
    ((filtered_df['Subscription period'].isna()) | (filtered_df['Subscription period'].isin(['0', 0, '0-0'])))
]

# Некоректне або відсутнє джерело (Source)
invalid_source = filtered_df[
    (filtered_df['Source'].isna()) | 
    (filtered_df['Source'].astype(str).str.lower().isin(['unknown', 'other', '-', 'none', '', 'nan']))
]

# --- 2. ЗБІР УСІХ ПРОБЛЕМ В ОДИН СПИСОК ---
issues = []

for _, row in missing_closing_date.iterrows():
    issues.append({"Тип": "📅 Відсутня Closing Date", "ID/Source": row['Source'], "Stage": row['Stage'], "Країна": row['Client country']})

for _, row in invalid_loss_reason.iterrows():
    issues.append({"Тип": "💬 Пуста/коротка причина програшу", "ID/Source": row['Source'], "Stage": row['Stage'], "Країна": row['Client country']})

for _, row in zero_budget_won.iterrows():
    issues.append({"Тип": "💰 Аномалія: Win з бюджетом 0", "ID/Source": row['Source'], "Stage": row['Stage'], "Країна": row['Client country']})

for _, row in missing_subscription.iterrows():
    issues.append({"Тип": "❌ Помилка: Won без підписки", "ID/Source": row['Source'], "Stage": row['Stage'], "Країна": row['Client country']})

for _, row in invalid_source.iterrows():
    issues.append({"Тип": "📢 Некоректне джерело (Source)", "ID/Source": "Check CRM", "Stage": row['Stage'], "Країна": row['Client country']})

# --- 3. ВІДОБРАЖЕННЯ РЕЗУЛЬТАТІВ ---

if issues:
    issues_df = pd.DataFrame(issues)
    # Робимо нумерацію з 1
    issues_df.index = issues_df.index + 1
    
    st.warning(f"Знайдено записів, що потребують уваги: {len(issues_df)}")
    
    # Виводимо таблицю. Використовуємо st.dataframe для зручного скролу та сортування
    st.dataframe(issues_df, use_container_width=True)
    
    # Додаємо кнопку завантаження для менеджерів
    csv = issues_df.to_csv(index=True).encode('utf-8-sig')
    st.download_button(
        label="📥 Завантажити список помилок у CSV",
        data=csv,
        file_name="crm_data_issues.csv",
        mime="text/csv",
    )
else:
    st.success("Проблем з валідацією даних не виявлено! Всі поля заповнені коректно. ✅")



    
# --- RevOps Insights Summary: ПОВНЕ ОНОВЛЕННЯ ---
st.divider()
st.header("🚀 RevOps Insights Summary")

# --- 1. ПІДГОТОВКА ДАНИХ ТА РОЗРАХУНОК МЕТРИК ---
total_count = len(filtered_df)
closed_deals = filtered_df[filtered_df['Stage'].isin(['Closed Won', 'Closed Lost'])]
won_deals_count = len(filtered_df[filtered_df['Stage'] == 'Closed Won'])
total_win_rate = (won_deals_count / len(closed_deals) * 100) if len(closed_deals) > 0 else 0

# СУВОРА ЛОГІКА ГІГІЄНИ: рахуємо % повністю чистих рядків
problematic_deals_ids = issues_df['ID/Source'].unique() if not issues_df.empty else []
problematic_count = len([x for x in problematic_deals_ids if x != "Check CRM"]) # ігноруємо технічні заглушки
clean_deals_ratio = (total_count - problematic_count) / total_count if total_count > 0 else 1
hygiene_score = clean_deals_ratio * 100

# РОЗРАХУНОК SALES CYCLE (Відносний: Closing - AQL)
temp_df = filtered_df.copy()
temp_df['AQL date'] = pd.to_datetime(temp_df['AQL date'], errors='coerce')
temp_df['Closing Date'] = pd.to_datetime(temp_df['Closing Date'], errors='coerce')
temp_df['cycle_days'] = (temp_df['Closing Date'] - temp_df['AQL date']).dt.days

# Беремо середнє лише для позитивних значень (де дата закриття після створення)
avg_cycle = temp_df[temp_df['cycle_days'] >= 0]['cycle_days'].mean()
avg_cycle_text = f"{int(avg_cycle)} днів" if not pd.isna(avg_cycle) else "N/A"

# --- 2. ВІЗУАЛІЗАЦІЯ ВЕРХНЬОГО РІВНЯ (Metrics) ---
col_m1, col_m2, col_m3, col_m4 = st.columns(4)

with col_m1:
    st.metric("Overall Win Rate", f"{total_win_rate:.1f}%")

with col_m2:
    # Відображаємо суворий Score з дельтою
    st.metric(
        "Data Hygiene Score", 
        f"{hygiene_score:.1f}%", 
        delta=f"-{100-hygiene_score:.1f}%" if hygiene_score < 100 else None,
        delta_color="inverse"
    )

with col_m3:
    st.metric("Avg Sales Cycle", avg_cycle_text)

with col_m4:
    top_budget = filtered_df['PPC budget USD'].value_counts().idxmax() if not filtered_df.empty else "N/A"
    st.metric("Core Segment", top_budget)

# --- 3. ГЛИБОКІ ІНСАЙТИ ---
st.write("### 🔍 Глибокий аналіз ефективності")
col_insight1, col_insight2 = st.columns(2)

with col_insight1:
    # АНАЛІЗ ЯКОСТІ ДЖЕРЕЛ
    source_stats = closed_deals.groupby('Source').agg(
        Count=('Is_Won', 'count'),
        Win_Rate=('Is_Won', 'mean')
    ).reset_index()
    
    reliable_sources = source_stats[source_stats['Count'] > 2]
    
    if not reliable_sources.empty:
        # Найкраще джерело
        best_source = reliable_sources.loc[reliable_sources['Win_Rate'].idxmax()]
        st.success(f"💎 **Джерело-зірка:** {best_source['Source']} (WR: {best_source['Win_Rate']*100:.1f}%)")
        
        # Пошук найгіршого джерела з цифрами порівняння
        worst_source = reliable_sources.loc[reliable_sources['Win_Rate'].idxmin()]
        
        # Вираховуємо, у скільки разів воно гірше за середнє
        if total_win_rate > 0:
            ratio = total_win_rate / (worst_source['Win_Rate'] * 100) if worst_source['Win_Rate'] > 0 else 0
            
            if worst_source['Win_Rate'] < (total_win_rate / 100 * 0.7): # Якщо WR джерела на 30% нижче середнього
                st.error(
                    f"⚠️ **Проблема якості:** {worst_source['Source']} "
                    f"(WR: {worst_source['Win_Rate']*100:.1f}%). "
                    f"Це в {ratio:.1f}x рази нижче за середній показник по компанії ({total_win_rate:.1f}%)."
                )
    else:
        st.info("ℹ️ Недостатньо даних для аналізу якості джерел.")

with col_insight2:
    # --- АНАЛІЗ ВУЗЬКИХ МІСЦЬ ТА ЗДОРОВ'Я ПАЙПЛАЙНУ ---
    
    # 1. Визначаємо умовне "сьогодні" (макс. дата в базі)
    latest_date = temp_df['Closing Date'].max()
    
    # 2. Фільтруємо відкриті угоди
    open_deals = temp_df[~temp_df['Stage'].isin(['Closed Won', 'Closed Lost'])].copy()
    
    if not open_deals.empty:
        # Рахуємо "вік" кожної відкритої угоди відносно останньої дати бази
        open_deals['days_stuck'] = (latest_date - open_deals['AQL date']).dt.days
        
        # Визначаємо поріг "застарівання" (на основі середнього циклу)
        stale_threshold = avg_cycle * 1.2 if not pd.isna(avg_cycle) else 30
        stale_deals_count = len(open_deals[open_deals['days_stuck'] > stale_threshold])
        
        st.info(f"⏳ **Pipeline Health:** {len(open_deals)} угод у роботі.")
        
        if stale_deals_count > 0:
            st.warning(f"⚠️ **Ризик:** {stale_deals_count} угод 'живуть' довше норми ({int(stale_threshold)} дн.)")
        
        # 3. ВІЗУАЛІЗАЦІЯ: Гістограма розподілу віку угод
        import plotly.express as px
        
        fig_age = px.histogram(
            open_deals, 
            x="days_stuck", 
            nbins=20,
            title="Розподіл угод за 'віком' (днів у роботі)",
            labels={'days_stuck': 'Кількість днів з моменту AQL', 'count': 'Кількість угод'},
            color_discrete_sequence=['#636EFA']
        )
        # Додаємо лінію порогу
        fig_age.add_vline(x=stale_threshold, line_dash="dash", line_color="red", 
                          annotation_text="Поріг застарівання", annotation_position="top right")
        
        st.plotly_chart(fig_age, use_container_width=True)
        
        # Виводимо стадію-завал
        top_stuck_stage = open_deals['Stage'].value_counts().idxmax()
        st.write(f"📍 Найбільший завал на стадії: **{top_stuck_stage}**")
        
    else:
        st.success("✅ Всі угоди закриті. Пайплайн порожній.")

# --- 4. АВТОМАТИЧНІ РЕКОМЕНДАЦІЇ ---
st.subheader("📝 Рекомендації для RevOps:")

recoms = []
if total_win_rate < 30:
    recoms.append("- 📉 **Конверсія:** Win Rate нижче ринкового середнього. Перевірте етап кваліфікації (AQL → SQL).")
if hygiene_score < 80:
    recoms.append("- 🧹 **Гігієна:** Понад 20% ваших даних мають критичні помилки. Звіти можуть бути неточними.")
if not pd.isna(avg_cycle) and avg_cycle > 30:
    recoms.append(f"- 🕒 **Швидкість:** Середній цикл ({int(avg_cycle)} дн.) задовгий для вашого сегменту. Шукайте затримки в 'Negotiations'.")

if recoms:
    for r in recoms:
        st.write(r)
else:

    st.write("✅ Всі ключові показники в нормі. Дані чисті, конверсія стабільна.")


