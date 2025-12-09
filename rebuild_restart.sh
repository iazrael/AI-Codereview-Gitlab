#!/bin/bash

# 先修改 Dockerfile 中的版本号
# RUN echo "v1.0.1" > .version
# 修改 其中的 v1.0.1，把末尾数字加一后写回去

# 提取 Dockerfile 中的版本号行
VERSION_LINE=$(grep -E 'RUN echo "v[0-9]+\.[0-9]+\.[0-9]+" > \.version' Dockerfile)

if [ -z "$VERSION_LINE" ]; then
    echo "未找到版本号行"
    exit 1
fi

# 提取版本号字符串，例如 v1.0.1
VERSION=$(echo "$VERSION_LINE" | sed -E 's/.*"([^"]+)".*/\1/')

# 分解版本号
MAJOR=$(echo "$VERSION" | cut -d. -f1 | sed 's/v//')
MINOR=$(echo "$VERSION" | cut -d. -f2)
PATCH=$(echo "$VERSION" | cut -d. -f3)

# 将末尾数字加一
NEW_PATCH=$((PATCH + 1))

# 构造新的版本号
NEW_VERSION="v${MAJOR}.${MINOR}.${NEW_PATCH}"

# 替换 Dockerfile 中的版本号
sed -i "s/RUN echo \"$VERSION\" > \.version/RUN echo \"$NEW_VERSION\" > .version/" Dockerfile

echo "版本号已从 $VERSION 更新为 $NEW_VERSION"

# 重新构建并重启服务
docker compose -f docker-compose.rq.yml build
docker compose -f docker-compose.rq.yml down
docker compose -f docker-compose.rq.yml up -d

echo "服务已重新构建并启动，新版本号: $NEW_VERSION"