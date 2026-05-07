from services.email_notifier import send_email


def main():
    delivered = send_email(
        "Тест email Price Monitor",
        "Это тестовое письмо для проверки SMTP-настроек Price Monitor.",
    )
    print(f"delivered={delivered}")


if __name__ == "__main__":
    main()
