lsof -t -i:8080 -i:4401 -i:4501 -i:4400 -i:9000 -i:9099 -i:9199 -i:9090 | xargs kill -9
firebase emulators:start --only firestore --project data8x-scratch > /dev/null 2>&1 &
pytest "$@"
lsof -t -i:8080 -i:4401 -i:4501 -i:4400 -i:9000 -i:9099 -i:9199 -i:9090 | xargs kill -9