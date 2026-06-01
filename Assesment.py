import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns


df = sns.load_dataset('geyser')

print(df.shape,"shape")



# Head (first 5 rows)
print("\nHead:",df.head())


# Info (structure of data)
print("\nInfo:",df.info())


# Describe (statistical summary)
print("\nDescribe:",df.describe())

#Missing value

df['duration'] = df['duration'].fillna(df['duration'].mean())
df['waiting'] = df['waiting'].fillna(df['waiting'].mean())

print("\nAfter cleaning:",df.isnull().sum())


df['eruption_type'] = df['duration'].apply(
    lambda x: 'Short' if x < 3 else 'Long'
)


print("\nNew Feature Added:",df[['duration', 'eruption_type']].head())


duration_arr = np.array(df['duration'])
waiting_arr = np.array(df['waiting'])

#print(duration_arr,'duration.array')


mean_duration = np.mean(duration_arr)
print("Mean duration (NumPy):", mean_duration)


max_waiting = np.max(waiting_arr)
print("Max waiting (NumPy):", max_waiting)


# Create figure
fig, axes = plt.subplots(2, 2, figsize=(14, 10))
fig.suptitle("Geyser Data Visualization", fontsize=16, fontweight='bold')

# 1. Histogram (Chart 1)
ax = axes[0, 0]
ax.hist(df['duration'], bins=20, color='skyblue')
ax.set_title("1. Distribution of Duration")
ax.set_xlabel("Duration")
ax.set_ylabel("Frequency")

# Annotation
ax.annotate("Peak",
            xy=(df['duration'].mean(), 20),
            xytext=(4, 30),
            arrowprops=dict(facecolor='black'))

# 2. Scatter Plot (Chart 2)
ax = axes[0, 1]
ax.scatter(df['duration'], df['waiting'], color='green', alpha=0.6)
ax.set_title("2. Duration vs Waiting Time")
ax.set_xlabel("Duration")
ax.set_ylabel("Waiting")

# Annotation
ax.annotate("Trend",
            xy=(4, 80),
            xytext=(2, 90),
            arrowprops=dict(facecolor='black'))

# 3. Box Plot (Chart 3)
ax = axes[1, 0]
sns.boxplot(x='kind', y='duration', data=df, ax=ax)
ax.set_title("3. Duration by Eruption Type")
ax.set_xlabel("Eruption Type")
ax.set_ylabel("Duration")

# Annotation
ax.annotate("Short vs Long",
            xy=(0, 2),
            xytext=(0.5, 4.5),
            arrowprops=dict(facecolor='black'))

#4. Count Plot (Chart 4)

ax = axes[1, 1]
sns.countplot(x='kind', hue='kind', data=df, palette='Set2', ax=ax, legend=False)
ax.set_title("4. Count of Eruption Type")
ax.set_xlabel("Eruption Type")
ax.set_ylabel("Count")

# Annotation
counts = df['kind'].value_counts()
ax.annotate(f"Max: {counts.max()}",
            xy=(0, counts.max()),
            xytext=(0.5, counts.max() + 10),
            arrowprops=dict(facecolor='black'))

# Adjust layout
plt.tight_layout()
plt.show()


#Key Insights


print("\n Key Insights:")

# Histogram Insight
print("1. The histogram shows a bimodal distribution of eruption duration, indicating two common types of eruptions: short and long.")

# Scatter Plot Insight
print("2. The scatter plot shows a positive relationship between duration and waiting time — longer eruptions lead to longer waiting periods.")

# Box Plot Insight
print("3. The boxplot highlights a clear separation between short and long eruptions with minimal overlap.")

