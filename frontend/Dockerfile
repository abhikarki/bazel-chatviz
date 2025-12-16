# base image for this stage
FROM node:20-alpine AS build

WORKDIR /app

COPY package.json package-lock.json* ./

# clean install, deletes existing node_modules before installing
RUN npm ci

COPY . .

# compile
RUN npm run build

# start new image, a fast image based on the Nginx web server on Alpine Linux. 
# This image does not contain Node.js runtime or large node_modules from previous stage.
FROM nginx:alpine AS production

# copy the nginx.conf to standard Nginx configuration directory
COPY nginx:conf /etc/nginx/conf.d/default.conf

# only copy lightweight compiled files from /app/dist/ and place them in nginx default serving directory
COPY --from=build /app/dist /usr/share/nginx/html

# listen on port 80
EXPOSE 80

# run the nginx web server
CMD ["nginx", "-g", "daemon"]