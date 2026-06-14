from ai.decision import evaluate_discard


def main():
    raw = input("Enter tiles separated by spaces:\n> ")
    tile, score = evaluate_discard(raw.split())
    print(f"Best discard: {tile}")
    print(f"Score: {score}")


if __name__ == "__main__":
    main()
