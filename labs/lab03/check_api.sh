#!/usr/bin/env bash
# Відтворювані перевірки із завдання 3 (сценарії 2–13).
# Запускати на щойно заповненій базі при запущеному сервері:
#   bash labs/lab03/check_api.sh
set -u
API="${API:-http://127.0.0.1:8000}"
JSON="Content-Type: application/json"

step() { printf '\n### %s\n' "$*"; }
call() {
    # call METHOD PATH [BODY]
    local method="$1" path="$2" body="${3:-}"
    printf '$ %s %s %s\n' "$method" "$path" "$body"
    if [ -n "$body" ]; then
        curl -s -X "$method" "$API$path" -H "$JSON" -d "$body" -w '\nHTTP %{http_code}\n'
    else
        curl -s -X "$method" "$API$path" -w '\nHTTP %{http_code}\n'
    fi
}
count() {
    curl -s "$API/records?limit=100" | python3 -c 'import json,sys; print(len(json.load(sys.stdin)))'
}

step "2. Службові маршрути"
call GET /ping
call GET /student
call GET /categories

step "3. CRUD окремого запису"
created=$(curl -s -X POST "$API/records" -H "$JSON" \
    -d '{"code":"V10-TEST","title":"Вимірювання сервера тест","category_id":1,"value":85.5,"status":"new"}')
echo "\$ POST /records -> $created"
id=$(printf '%s' "$created" | python3 -c 'import json,sys; print(json.load(sys.stdin)["id"])')
call GET "/records/$id"
call PUT "/records/$id" '{"code":"V10-TEST","title":"Вимірювання сервера тест (оновлено)","category_id":3,"value":42.0,"status":"done"}'
call DELETE "/records/$id"
call GET "/records/$id"

step "4. Фільтри та сторінки"
call GET "/records?category_id=1"
call GET "/records?status=new&min_value=80"
call GET "/records?q=%D1%81%D0%B5%D1%80%D0%B2%D0%B5%D1%80%D0%B0%2001"
call GET "/records?limit=3&offset=0"
call GET "/records?limit=3&offset=3"
call GET "/records?category_id=999"

step "5. Некоректні дані (очікується 422, база не змінюється)"
echo "Записів до: $(count)"
call POST /records '{"code":"V10-BAD1","title":"Негативне значення","category_id":1,"value":-5,"status":"new"}'
call POST /records '{"code":"V10-BAD2","title":"   ","category_id":1,"value":50,"status":"new"}'
call POST /records '{"code":"V10-BAD3","title":"Невідомий статус","category_id":1,"value":50,"status":"closed"}'
call GET "/records?limit=0"
echo "Записів після: $(count)"

step "6. Значення понад верхню межу"
call POST /records '{"code":"V10-BAD4","title":"Понад 100 відсотків","category_id":1,"value":100.5,"status":"new"}'
call GET "/records?min_value=101"

step "7. Неіснуючі запис і категорія (404)"
call GET /records/9999
call POST /records '{"code":"V10-NOCAT","title":"Без категорії","category_id":99,"value":10,"status":"new"}'

step "8. Дублікати (409)"
call POST /records '{"code":"V10-01","title":"Дублікат коду","category_id":1,"value":10,"status":"new"}'
call POST /categories '{"name":"cpu"}'
call GET /records/1

step "9. Видалення категорій"
call DELETE /categories/1
call POST /categories '{"name":"network"}'
new_cat=$(curl -s "$API/categories" | python3 -c 'import json,sys; print(json.load(sys.stdin)[-1]["id"])')
call DELETE "/categories/$new_cat"
call GET /categories

step "10. Коректний пакет із двох записів"
call POST /records/bulk '[{"code":"V10-B01","title":"Пакетне вимірювання 01","category_id":1,"value":70,"status":"new"},{"code":"V10-B02","title":"Пакетне вимірювання 02","category_id":2,"value":95,"status":"in_progress"}]'

step "11. Пакет: другий code уже є в базі (409, нічого не збережено)"
echo "Записів до: $(count)"
call POST /records/bulk '[{"code":"V10-ROLLBACK","title":"Перший елемент","category_id":1,"value":40,"status":"new"},{"code":"V10-01","title":"Дублікат коду","category_id":2,"value":50,"status":"new"}]'
echo "Записів після: $(count)"
call GET "/records?q=%D0%9F%D0%B5%D1%80%D1%88%D0%B8%D0%B9"

step "12. Пакет: друга категорія не існує (404, нічого не збережено)"
echo "Записів до: $(count)"
call POST /records/bulk '[{"code":"V10-ROLLBACK","title":"Перший елемент","category_id":1,"value":40,"status":"new"},{"code":"V10-NOCAT2","title":"Неіснуюча категорія","category_id":42,"value":50,"status":"new"}]'
echo "Записів після: $(count)"

step "13. Спроба SQL-ін'єкції в q"
echo "Записів до: $(count)"
call GET "/records?q=%27%20OR%201%3D1%20--"
echo "Записів після: $(count)"
