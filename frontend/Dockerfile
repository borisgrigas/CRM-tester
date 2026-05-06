FROM node:20-alpine

WORKDIR /app
ENV CI=true

COPY package.json yarn.lock* ./
RUN corepack enable && yarn install --frozen-lockfile || yarn install

COPY . .

EXPOSE 3000
CMD ["yarn", "start"]
