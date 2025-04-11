import requests
import matplotlib.pyplot as plt
import statistics
import json
from datetime import datetime

CITY_CODES = {
    1: {"name": "Москва", "code": 1},
    2: {"name": "Санкт-Петербург", "code": 2},
    3: {"name": "Казань", "code": 88}
}


def get_hh_vacancies(search_text, city_code):
    api_url = "https://api.hh.ru/vacancies"
    vacancies_data = []

    for page in range(3):
        params = {
            "text": search_text,
            "area": city_code,
            "per_page": 100,
            "page": page,
            "only_with_salary": True
        }

        try:
            response = requests.get(api_url, params=params, timeout=10)
            response.raise_for_status()
            data = response.json()

            for vacancy in data.get("items", []):
                salary = process_salary(vacancy.get("salary"))
                if salary:
                    vacancies_data.append({
                        "name": vacancy.get("name"),
                        "salary": salary,
                        "url": vacancy.get("alternate_url"),
                        "employer": vacancy.get("employer", {}).get("name"),
                        "published_at": vacancy.get("published_at")
                    })

        except requests.exceptions.RequestException as e:
            print(f"Ошибка при запросе: {e}")
            break

    return vacancies_data


def process_salary(salary_data):
    if not salary_data or salary_data.get("currency") != "RUR":
        return None

    from_, to_ = salary_data.get("from"), salary_data.get("to")
    if from_ and to_:
        return (from_ + to_) / 2
    return from_ or to_


def analyze_and_plot(vacancies_data, city_name, vacancy_name):
    if not vacancies_data:
        print("\nНет данных для анализа.")
        return

    salaries = [v["salary"] for v in vacancies_data]

    print(f"\nАнализ зарплат для '{vacancy_name}' в {city_name}:")
    print(f"Количество вакансий: {len(vacancies_data)}")
    print(f"Максимальная зарплата: {max(salaries):,.0f} руб".replace(",", " "))
    print(f"Минимальная зарплата: {min(salaries):,.0f} руб".replace(",", " "))
    print(f"Средняя зарплата: {statistics.mean(salaries):,.0f} руб".replace(",", " "))
    print(f"Медиана: {statistics.median(salaries):,.0f} руб".replace(",", " "))

    plt.figure(figsize=(15, 5))

    plt.subplot(1, 3, 1)
    plt.scatter(range(len(salaries)), salaries, alpha=0.5)
    plt.title("Разброс зарплат")
    plt.xlabel("Номер вакансии")
    plt.ylabel("Рубли")

    plt.subplot(1, 3, 2)
    plt.boxplot(salaries, patch_artist=True)
    plt.title("Распределение зарплат")

    plt.subplot(1, 3, 3)
    plt.hist(salaries, bins=15, edgecolor='black')
    plt.title("Частота зарплат")
    plt.xlabel("Рубли")

    plt.suptitle(f"Зарплаты для '{vacancy_name}' в {city_name}", fontweight='bold')
    plt.tight_layout()
    plt.show()

    save_results(vacancies_data, city_name, vacancy_name)


def save_results(data, city_name, vacancy_name):
    filename = f"results_{vacancy_name}_{city_name}_{datetime.now().strftime('%Y%m%d_%H%M')}.json"
    try:
        with open(filename, "w", encoding="utf-8") as f:
            json.dump({
                "metadata": {
                    "query": vacancy_name,
                    "city": city_name,
                    "generated_at": datetime.now().isoformat(),
                    "count": len(data)
                },
                "vacancies": sorted(data, key=lambda x: x["salary"], reverse=True)
            }, f, ensure_ascii=False, indent=2)
        print(f"\nРезультаты сохранены в файл: {filename}")
    except IOError as e:
        print(f"\nОшибка при сохранении результатов: {e}")


def main():
    print("\nВыберите город:")
    print("1 - Москва")
    print("2 - Санкт-Петербург")
    print("3 - Казань")

    try:
        city_choice = int(input("Ваш выбор (1-3): "))
        city_data = CITY_CODES.get(city_choice)
        if not city_data:
            raise ValueError("Неверный выбор города")

        vacancy_name = input("Введите название вакансии: ").strip()
        if not vacancy_name:
            raise ValueError("Название вакансии не может быть пустым")

        vacancies = get_hh_vacancies(vacancy_name, city_data["code"])
        analyze_and_plot(vacancies, city_data["name"], vacancy_name)

    except ValueError as e:
        print(f"Ошибка ввода: {e}")
    except Exception as e:
        print(f"Произошла непредвиденная ошибка: {e}")


if __name__ == "__main__":
    main()