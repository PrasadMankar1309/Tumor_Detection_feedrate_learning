// Firebase Configuration provided by the user
const firebaseConfig = {
    apiKey: "AIzaSyBn2LQ3za6C51pHNb7RwonzrXLZZ35ur4c",
    authDomain: "brain-tumor-712ff.firebaseapp.com",
    databaseURL: "https://brain-tumor-712ff-default-rtdb.firebaseio.com",
    projectId: "brain-tumor-712ff",
    storageBucket: "brain-tumor-712ff.firebasestorage.app",
    messagingSenderId: "6860284662",
    appId: "1:6860284662:web:313bba23db4af69a4802d7",
    measurementId: "G-XJZTKTKM23"
};

// Initialize Firebase
if (!firebase.apps.length) {
    firebase.initializeApp(firebaseConfig);
}

// Global Firebase Service References
const auth = firebase.auth();
const database = firebase.database();
const storage = firebase.storage();
