COMMIT=$(git rev-parse HEAD)
BRANCH=$(git symbolic-ref HEAD | sed 's!refs\/heads\/!!')
DATE=$(date -u +"%Y-%m-%dT%H:%M:%SZ")
VERSION=$(git describe --tags --abbrev=0)

[ ${#VERSION} == 0 ] && VERSION="no version"
echo "{
\"commit\":  \"$COMMIT\",
\"date\":    \"$DATE\",
\"branch\":  \"$BRANCH\",
\"version\": \"$VERSION\"
}"