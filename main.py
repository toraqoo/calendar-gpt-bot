parsed = extract_dates_from_text(user_input)
dates = parsed['dates']
time_filter = parsed['time_filter']
keyword_filter = parsed['keyword_filter']
find_available = parsed['find_available']

events = get_events(dates)
if find_available:
    available_days = find_available_days(events, dates, time_filter=time_filter)
    if not available_days:
        return "❌ 요청한 조건에 맞는 '한가한 날'이 없습니다."
    return format_available_days(available_days)

# 기본 일정 출력
filtered_events = filter_events(events, time_filter=time_filter, keyword_filter=keyword_filter)
if not filtered_events:
    return "❌ 해당 조건에 맞는 일정이 없습니다."
return format_event_list(filtered_events)
