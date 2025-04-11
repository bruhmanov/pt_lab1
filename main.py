import requests
from datetime import datetime
import statistics
import matplotlib.pyplot as plt
import json
import numpy as np

CITIES = {
    1: {'name': 'Москва', 'code': 1},
    2: {'name': 'Санкт-Петербург', 'code': 2},
    3: {'name': 'Казань', 'code': 88}
}


def get_vacancies_from_hh(search_text, city_code, max_pages=3):
    vacancies = []

    for page in range(max_pages):
        try:
            params = {
                'text': search_text,
                'area': city_code,
                'page': page,
                'per_page': 100,
                'only_with_salary': True
            }

            resp = requests.get("https://api.hh.ru/vacancies", params=params, timeout=15)
            resp.raise_for_status()

            data = resp.json()
            if not data.get('items'):
                break

            for item in data['items']:
                salary = parse_salary(item.get('salary'))
                if salary:
                    vacancies.append({
                        'title': item.get('name'),
                        'salary': salary,
                        'link': item.get('alternate_url'),
                        'company': item.get('employer', {}).get('name'),
                        'date': item.get('published_at')
                    })

        except requests.exceptions.RequestException as e:
            print(f"Ошибка при запросе страницы {page}: {e}")
            continue

    return vacancies


def parse_salary(salary_data):
    if not salary_data or salary_data.get('currency') != 'RUR':
        return None

    salary_from = salary_data.get('from')
    salary_to = salary_data.get('to')

    if salary_from and salary_to:
        return (salary_from + salary_to) // 2
    return salary_from or salary_to


def calculate_stats(salaries):
    if not salaries:
        return None

    q1 = int(np.quantile(salaries, 0.25))
    q3 = int(np.quantile(salaries, 0.75))

    stats = {
        'count': len(salaries),
        'min': min(salaries),
        'max': max(salaries),
        'mean': int(statistics.mean(salaries)),
        'median': int(statistics.median(salaries)),
        'stdev': int(statistics.stdev(salaries)),
        'q1': q1,
        'q3': q3,
        'iqr': q3 - q1
    }

    return stats


def draw_salary_plots(salaries, stats, title):
    plt.figure(figsize=(15, 6))

    plt.subplot(1, 3, 1)
    plt.scatter(range(len(salaries)), salaries, alpha=0.6, color='blue')
    plt.title('Разброс зарплат')
    plt.xlabel('Номер вакансии')
    plt.ylabel('Рубли')
    plt.grid(True, alpha=0.3)

    plt.subplot(1, 3, 2)
    plt.boxplot(salaries, vert=True, patch_artist=True)
    plt.title('Распределение зарплат')

    plt.text(1.1, stats['q1'], f"25% ≤ {stats['q1']:,}р".replace(',', ' '),
             va='center', fontsize=9)
    plt.text(1.1, stats['q3'], f"75% ≤ {stats['q3']:,}р".replace(',', ' '),
             va='center', fontsize=9)

    plt.subplot(1, 3, 3)
    n_bins = min(15, len(salaries) // 2)
    plt.hist(salaries, bins=n_bins, color='green', edgecolor='black', alpha=0.7)

    plt.axvline(stats['mean'], color='red', linestyle='--', label=f'Среднее ({stats["mean"]:,}р)')
    plt.axvline(stats['median'], color='blue', linestyle='-', label=f'Медиана ({stats["median"]:,}р)')
    plt.legend()

    plt.title('Гистограмма зарплат')
    plt.xlabel('Диапазон зарплат')
    plt.ylabel('Количество вакансий')

    plt.suptitle(title, fontsize=14, fontweight='bold')
    plt.tight_layout()
    plt.show()


def save_results(vacancies, stats, query, city_name):
    if not vacancies:
        print("Нет данных для сохранения")
        return

    filename = f"hh_{query}_{city_name}_{datetime.now().strftime('%d%m%Y')}.json"

    result = {
        'info': {
            'query': query,
            'city': city_name,
            'date': datetime.now().strftime('%Y-%m-%d %H:%M'),
            'total': len(vacancies)
        },
        'stats': stats,
        'top_vacancies': sorted(vacancies, key=lambda x: x['salary'], reverse=True)[:50]
    }

    try:
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(result, f, ensure_ascii=False, indent=2)
        print(f"Данные сохранены в файл: {filename}")
    except Exception as e:
        print(f"Ошибка при сохранении: {e}")


def main():
    print("\nДоступные города:")
    for num, city in CITIES.items():
        print(f"{num} — {city['name']}")

    try:
        city_num = int(input("\nВыберите город (1-3): "))
        selected_city = CITIES.get(city_num)
        if not selected_city:
            raise ValueError("Нет такого города")

        query = input("Введите название профессии: ").strip()

        vacancies = get_vacancies_from_hh(query, selected_city['code'])

        if not vacancies:
            print("Не найдено вакансий по вашему запросу")
            return

        salaries = [v['salary'] for v in vacancies]
        stats = calculate_stats(salaries)

        print(f"\nРезультаты для '{query}' в {selected_city['name']}")
        print(f"Всего вакансий: {stats['count']}")
        print(f"Мин/Макс: {stats['min']:,} — {stats['max']:,} руб".replace(',', ' '))
        print(f"Средняя: {stats['mean']:,} руб".replace(',', ' '))
        print(f"Медиана: {stats['median']:,} руб".replace(',', ' '))
        print(f"Стандартное отклонение: ±{stats['stdev']:,} руб".replace(',', ' '))
        print(f"Межквартильный размах: {stats['iqr']:,} руб".replace(',', ' '))
        print(f"25% вакансий ≤ {stats['q1']:,} руб, 75% ≤ {stats['q3']:,} руб".replace(',', ' '))

        plot_title = f"Зарплаты '{query}' в {selected_city['name']}\n(найдено {stats['count']} вакансий)"
        draw_salary_plots(salaries, stats, plot_title)

        save_results(vacancies, stats, query, selected_city['name'])

    except ValueError as e:
        print(f"\nОшибка: {e}")
    except Exception as e:
        print(f"\nЧто-то пошло не так: {e}")


if __name__ == '__main__':
    main()