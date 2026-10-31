"""python train.py --data data/dog_data.csv --output models/dog_model.joblib"""
import argparse
from core import DATA_PATH, MODEL_PATH, read_data, train_bundle, save_bundle, file_digest


def main():
    parser = argparse.ArgumentParser(description="DogCareAI 가상 사례 분류·군집·유사 사례 모델 학습")
    parser.add_argument("--data", default=str(DATA_PATH))
    parser.add_argument("--output", default=str(MODEL_PATH))
    args = parser.parse_args()
    try:
        data = read_data(args.data, training=True)
        bundle = train_bundle(data, file_digest(args.data))
        save_bundle(bundle, args.output)
    except (ValueError, OSError) as exc:
        parser.exit(1, f"학습 실패: {exc}\n")
    m = bundle["metrics"]
    print(f"{m['rows']}행, {m['cv_folds']}개 그룹 교차검증 완료")
    print(f"가상 라벨 재현 정확도: {m['oof_accuracy']:.1%}, macro F1: {m['oof_macro_f1']:.3f}")
    print(f"최빈 라벨 기준선: {m['baseline_accuracy']:.1%}")
    print(m["interpretation"])
    print(f"모델 저장: {args.output}")


if __name__ == "__main__":
    main()
