import requests
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
    MIN_SALARY_THRESHOLD = 5000

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
                if salary and salary >= MIN_SALARY_THRESHOLD:
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


def calculate_mean(salaries):
    return sum(salaries) / len(salaries)


def calculate_variance(salaries, mean):
    return sum((x - mean) ** 2 for x in salaries) / len(salaries)


def calculate_quantile(salaries, q):
    sorted_salaries = sorted(salaries)
    index = (len(sorted_salaries) - 1) * q
    lower = int(index)
    delta = index - lower

    if lower + 1 < len(sorted_salaries):
        return sorted_salaries[lower] * (1 - delta) + sorted_salaries[lower + 1] * delta
    return sorted_salaries[lower]


def calculate_stats(salaries):
    if not salaries:
        return None

    sorted_salaries = sorted(salaries)
    n = len(sorted_salaries)

    min_val = sorted_salaries[0]
    max_val = sorted_salaries[-1]
    range_val = max_val - min_val

    mean_val = calculate_mean(salaries)
    variance_val = calculate_variance(salaries, mean_val)
    stdev_val = variance_val ** 0.5

    q1 = calculate_quantile(sorted_salaries, 0.25)
    median = calculate_quantile(sorted_salaries, 0.5)
    q3 = calculate_quantile(sorted_salaries, 0.75)
    iqr = q3 - q1

    stats = {
        'count': n,
        'min': min_val,
        'max': max_val,
        'range': range_val,
        'mean': int(mean_val),
        'variance': int(variance_val),
        'stdev': int(stdev_val),
        'q1': int(q1),
        'median': int(median),
        'q3': int(q3),
        'iqr': int(iqr)
    }

    return stats


def histogram(salaries, n_bins):
    min_salary = max(0, min(salaries))
    max_salary = max(salaries)
    bin_width = (max_salary - min_salary) / n_bins
    bins = [min_salary + i * bin_width for i in range(n_bins + 1)]

    freq_counts = [0] * n_bins
    for salary in salaries:
        for i in range(n_bins):
            if bins[i] <= salary < bins[i + 1]:
                freq_counts[i] += 1
                break

    total = len(salaries)
    prob_counts = [count / total for count in freq_counts]

    return bins, freq_counts, prob_counts


def empirical_cdf(salaries):
    sorted_salaries = sorted(salaries)
    n = len(sorted_salaries)
    x = sorted_salaries
    y = [i / n for i in range(1, n + 1)]
    return x, y


def draw_plots(salaries, stats, title):
    plt.figure(figsize=(8, 6))
    plt.scatter(range(len(salaries)), salaries, alpha=0.6, color='blue')
    plt.xlabel('Номер вакансии')
    plt.ylabel('Зарплата (рубли)')
    plt.title('Разброс зарплат')
    plt.grid(True, alpha=0.3)
    plt.show()

    plt.figure(figsize=(8, 6))
    plt.boxplot(salaries, vert=True, patch_artist=True)
    plt.axhline(stats['q1'], color='orange', label='25% квартиль')
    plt.axhline(stats['median'], color='green', label='Медиана')
    plt.axhline(stats['q3'], color='purple', label='75% квартиль')
    plt.legend()
    plt.ylabel('Зарплата (рубли)')
    plt.title('Ящик с усами')
    plt.show()

    n_bins = min(15, len(salaries) // 2)
    bins, freq_counts, prob_counts = histogram(salaries, n_bins)
    bin_width = bins[1] - bins[0]

    plt.figure(figsize=(8, 6))
    plt.bar(bins[:-1], freq_counts, width=bin_width, color='green', edgecolor='black', alpha=0.7)
    plt.axvline(stats['mean'], color='red', linestyle='--', label=f'Среднее ({stats["mean"]:,} руб)')
    plt.axvline(stats['median'], color='blue', linestyle='-', label=f'Медиана ({stats["median"]:,} руб)')
    plt.legend()
    plt.xlabel('Зарплата (рубли)')
    plt.ylabel('Количество вакансий')
    plt.title('Частотная гистограмма')
    plt.grid(True, alpha=0.3)
    plt.xlim(0, max(salaries) * 1.1)
    plt.show()

    plt.figure(figsize=(8, 6))
    plt.bar(bins[:-1], prob_counts, width=bin_width, color='purple', edgecolor='black', alpha=0.7)
    plt.axvline(stats['mean'], color='red', linestyle='--', label=f'Среднее ({stats["mean"]:,} руб)')
    plt.axvline(stats['median'], color='blue', linestyle='-', label=f'Медиана ({stats["median"]:,} руб)')

    x = np.linspace(0, max(salaries), 100)
    norm_density = (1 / (stats['stdev'] * np.sqrt(2 * np.pi))) * np.exp(
        -0.5 * ((x - stats['mean']) / stats['stdev']) ** 2) * bin_width
    plt.plot(x, norm_density, color='orange', label='Нормальное распределение')

    plt.legend()
    plt.xlabel('Зарплата (рубли)')
    plt.ylabel('Плотность вероятности')
    plt.title('Вероятностная гистограмма')
    plt.grid(True, alpha=0.3)
    plt.xlim(0, max(salaries) * 1.1)
    plt.show()

    plt.figure(figsize=(8, 6))
    x, y = empirical_cdf(salaries)
    plt.step(x, y, color='blue', label='ЭФР')
    plt.axvline(stats['mean'], color='red', linestyle='--', label=f'Среднее ({stats["mean"]:,} руб)')
    plt.axvline(stats['median'], color='green', linestyle='-', label=f'Медиана ({stats["median"]:,} руб)')
    plt.legend()
    plt.xlabel('Зарплата (рубли)')
    plt.ylabel('F(x)')
    plt.title('Эмпирическая функция распределения')
    plt.grid(True, alpha=0.3)
    plt.xlim(0, max(salaries) * 1.1)
    plt.show()


def save_results(vacancies, stats, query, city_name):
    if not vacancies:
        print("Нет данных для сохранения")
        return

    filename = f"hh_{query}_{city_name}.json"

    result = {
        'info': {
            'query': query,
            'city': city_name,
            'total': len(vacancies)
        },
        'stats': stats,
        'vacancies': vacancies
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
        print(f"Размах: {stats['range']:,} руб".replace(',', ' '))
        print(f"Средняя: {stats['mean']:,} руб".replace(',', ' '))
        print(f"Медиана: {stats['median']:,} руб".replace(',', ' '))
        print(f"Стандартное отклонение: ±{stats['stdev']:,} руб".replace(',', ' '))
        print(f"Дисперсия: {stats['variance']:,} руб²".replace(',', ' '))
        print(f"Межквартильный размах: {stats['iqr']:,} руб".replace(',', ' '))
        print(f"Квартили: [{stats['q1']:,}, {stats['median']:,}, {stats['q3']:,}] руб".replace(',', ' '))

        plot_title = f"Зарплаты '{query}' в {selected_city['name']}\n(найдено {stats['count']} вакансий)"
        draw_plots(salaries, stats, plot_title)

        save_results(vacancies, stats, query, selected_city['name'])

    except ValueError as e:
        print(f"\nОшибка: {e}")
    except Exception as e:
        print(f"\nЧто-то пошло не так: {e}")


if __name__ == '__main__':
    main()