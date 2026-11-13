# Firebase Emulator Suite (Auth + Firestore) para desenvolvimento local e CI.
FROM node:22-slim
RUN apt-get update \
 && apt-get install -y --no-install-recommends openjdk-17-jre-headless \
 && rm -rf /var/lib/apt/lists/*
RUN npm install -g firebase-tools@13.35.1
WORKDIR /workspace
CMD ["firebase", "emulators:start", "--only", "auth,firestore", "--project", "demo-functional-agent"]
