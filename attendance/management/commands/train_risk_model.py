"""
Management command to train and evaluate the optional Decision Tree early-warning model.
"""

from django.core.management.base import BaseCommand
from attendance.services.ml_risk_service import generate_synthetic_dataset_and_train


class Command(BaseCommand):
    help = "Trains the Decision Tree attendance risk classifier and evaluates precision/recall/F1 metrics."

    def add_arguments(self, parser):
        parser.add_argument('--samples', type=int, default=600, help='Number of synthetic feature samples')

    def handle(self, *args, **options):
        samples = options['samples']
        self.stdout.write(f"Training Decision Tree Classifier on {samples} stratified samples...")

        metrics = generate_synthetic_dataset_and_train(n_samples=samples)

        self.stdout.write(self.style.SUCCESS(f"Model successfully trained! Accuracy: {metrics['accuracy']}%"))
        self.stdout.write("Classification Report Summary:")
        for label in metrics['class_labels']:
            stats = metrics['classification_report'].get(label, {})
            self.stdout.write(f"  Class {label:<10}: Precision={stats.get('precision', 0):.2f}, Recall={stats.get('recall', 0):.2f}, F1={stats.get('f1-score', 0):.2f}")
        
        self.stdout.write(f"Confusion Matrix (Rows: Actual, Cols: Predicted): {metrics['confusion_matrix']}")
        self.stdout.write(f"Feature Importances: {metrics['feature_importances']}")
