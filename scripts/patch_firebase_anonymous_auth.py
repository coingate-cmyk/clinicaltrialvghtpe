#!/usr/bin/env python3
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[1]
INDEX = ROOT / 'index.html'
s = INDEX.read_text(encoding='utf-8')

# 1) Load Firebase Auth compat next to the existing Firebase SDKs.
auth_tag = '    <script src="https://www.gstatic.com/firebasejs/10.12.2/firebase-auth-compat.js"></script>\n'
firestore_tag = '    <script src="https://www.gstatic.com/firebasejs/10.12.2/firebase-firestore-compat.js"></script>\n'
if auth_tag not in s:
    if firestore_tag not in s:
        raise SystemExit('Cannot locate Firebase Firestore script tag')
    s = s.replace(firestore_tag, auth_tag + firestore_tag, 1)

# 2) Replace the shared Firebase initializer with an auth-aware initializer.
old = '''let firebaseAppInstance = null;\nlet firestoreInstance = null;\n\nconst initializeFirebaseApp = (firebaseConfig) => {\n    if (!firebaseConfig || !firebaseConfig.apiKey || !firebaseConfig.projectId || !firebaseConfig.appId) {\n        throw new Error('Firebase 設定不完整');\n    }\n    if (!firebaseAppInstance) {\n        firebaseAppInstance = firebase.apps && firebase.apps.length\n            ? firebase.app()\n            : firebase.initializeApp(firebaseConfig);\n    }\n    if (!firestoreInstance) {\n        firestoreInstance = firebase.firestore();\n    }\n    return firestoreInstance;\n};\n'''
new = '''let firebaseAppInstance = null;\nlet firestoreInstance = null;\nlet firebaseAuthInstance = null;\nlet firebaseAuthReadyPromise = null;\n\nconst initializeFirebaseCore = (firebaseConfig) => {\n    if (!firebaseConfig || !firebaseConfig.apiKey || !firebaseConfig.projectId || !firebaseConfig.appId) {\n        throw new Error('Firebase 設定不完整');\n    }\n    if (!firebaseAppInstance) {\n        firebaseAppInstance = firebase.apps && firebase.apps.length\n            ? firebase.app()\n            : firebase.initializeApp(firebaseConfig);\n    }\n    if (!firestoreInstance) firestoreInstance = firebase.firestore();\n    if (!firebaseAuthInstance) firebaseAuthInstance = firebase.auth();\n    return { db: firestoreInstance, auth: firebaseAuthInstance };\n};\n\nconst ensureFirebaseAnonymousAuth = async (firebaseConfig) => {\n    const { db, auth } = initializeFirebaseCore(firebaseConfig);\n    if (auth.currentUser) return db;\n    if (!firebaseAuthReadyPromise) {\n        firebaseAuthReadyPromise = auth.signInAnonymously()\n            .then(() => db)\n            .catch((error) => {\n                firebaseAuthReadyPromise = null;\n                const code = error && error.code ? String(error.code) : '';\n                if (code.includes('operation-not-allowed')) {\n                    throw new Error('Firebase 匿名登入尚未在專案端啟用');\n                }\n                throw error;\n            });\n    }\n    return firebaseAuthReadyPromise;\n};\n\nconst initializeFirebaseApp = (firebaseConfig) => initializeFirebaseCore(firebaseConfig).db;\n'''
if old in s:
    s = s.replace(old, new, 1)
elif 'const ensureFirebaseAnonymousAuth = async (firebaseConfig)' not in s:
    raise SystemExit('Cannot locate Firebase initializer anchor')

# 3) Gate all Firestore reads/writes through anonymous auth.
replacements = {
"const subscribeFirestoreData = ({ firebaseConfig, onTrials, onSubjects, onStatus, onError }) => {\n    try {\n        const db = initializeFirebaseApp(firebaseConfig);":
"const subscribeFirestoreData = ({ firebaseConfig, onTrials, onSubjects, onStatus, onError }) => {\n    let cancelled = false;\n    let unsubscribe = () => {};\n    ensureFirebaseAnonymousAuth(firebaseConfig).then((db) => {\n        if (cancelled) return;",
"        return () => {\n            try { unsubTrials && unsubTrials(); } catch (e) {}\n            try { unsubSubjects && unsubSubjects(); } catch (e) {}\n        };\n    } catch (error) {\n        onError && onError(error);\n        return () => {};\n    }\n};":
"        unsubscribe = () => {\n            try { unsubTrials && unsubTrials(); } catch (e) {}\n            try { unsubSubjects && unsubSubjects(); } catch (e) {}\n        };\n    }).catch((error) => {\n        onError && onError(error);\n    });\n    return () => { cancelled = true; unsubscribe(); };\n};",
"const saveTrialToFirestore = async (firebaseConfig, trialData) => {\n    const db = initializeFirebaseApp(firebaseConfig);":
"const saveTrialToFirestore = async (firebaseConfig, trialData) => {\n    const db = await ensureFirebaseAnonymousAuth(firebaseConfig);",
"const deleteTrialFromFirestore = async (firebaseConfig, code) => {\n    const db = initializeFirebaseApp(firebaseConfig);":
"const deleteTrialFromFirestore = async (firebaseConfig, code) => {\n    const db = await ensureFirebaseAnonymousAuth(firebaseConfig);",
"const clearTrialsFromFirestore = async (firebaseConfig) => {\n    const db = initializeFirebaseApp(firebaseConfig);":
"const clearTrialsFromFirestore = async (firebaseConfig) => {\n    const db = await ensureFirebaseAnonymousAuth(firebaseConfig);",
"const saveSubjectsToFirestore = async (firebaseConfig, data) => {\n    const db = initializeFirebaseApp(firebaseConfig);":
"const saveSubjectsToFirestore = async (firebaseConfig, data) => {\n    const db = await ensureFirebaseAnonymousAuth(firebaseConfig);",
"const seedInitialTrialsToFirestore = async (firebaseConfig, trialsData) => {\n    const db = initializeFirebaseApp(firebaseConfig);":
"const seedInitialTrialsToFirestore = async (firebaseConfig, trialsData) => {\n    const db = await ensureFirebaseAnonymousAuth(firebaseConfig);",
"const publishPublicTrialsToFirestore = async (firebaseConfig, sourceTrials) => {\n    const db = initializeFirebaseApp(firebaseConfig);":
"const publishPublicTrialsToFirestore = async (firebaseConfig, sourceTrials) => {\n    const db = await ensureFirebaseAnonymousAuth(firebaseConfig);",
}

for a, b in replacements.items():
    if a in s:
        s = s.replace(a, b, 1)
    elif b not in s:
        raise SystemExit(f'Cannot locate expected Firebase auth patch anchor: {a[:80]}')

# Guard against accidental unauthenticated direct Firestore access in our app helpers.
for fn in ['saveTrialToFirestore','deleteTrialFromFirestore','clearTrialsFromFirestore','saveSubjectsToFirestore','seedInitialTrialsToFirestore','publishPublicTrialsToFirestore']:
    m = re.search(rf'const {fn} = async \([\s\S]*?\n}};', s)
    if not m or 'await ensureFirebaseAnonymousAuth' not in m.group(0):
        raise SystemExit(f'{fn} is not auth-gated')

INDEX.write_text(s, encoding='utf-8')
print('Firebase anonymous auth patch applied.')
