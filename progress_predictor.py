import pandas as pd
import numpy as np
from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import train_test_split
from sklearn.metrics import accuracy_score
import joblib

# Step 1: Generate dummy data with RULES
np.random.seed(42)
data = pd.DataFrame({
    'time_spent_hours': np.random.randint(1, 20, 200),
    'task_type': np.random.choice(['Onboarding', 'Training', 'Documentation'], 200),
    'previous_delays': np.random.randint(0, 5, 200),
})

# Step 2: Rule-based labels (instead of random)
def label(row):
    if row['time_spent_hours'] < 5 or row['previous_delays'] > 2:
        return 1   # Delayed
    else:
        return 0   # On Track

data['WillDelay'] = data.apply(label, axis=1)

# Step 3: Encode categorical features
data = pd.get_dummies(data, columns=['task_type'], drop_first=True)

# Step 4: Split
X = data.drop('WillDelay', axis=1)
y = data['WillDelay']
X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)

# Step 5: Train model
model = RandomForestClassifier(n_estimators=100, random_state=42)
model.fit(X_train, y_train)

# Step 6: Save model
joblib.dump(model, 'progress_model.pkl')
print("✅ Model trained and saved as progress_model.pkl")

# Step 7: Accuracy check
y_pred = model.predict(X_test)
print("Accuracy:", accuracy_score(y_test, y_pred))
