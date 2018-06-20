# Item Catalog Application #

Developed an application that provides a list of items within a variety of categories as well as provide a user registration and authentication system. Registered users will have the ability to post, edit and delete their own items.

## About the Project: ##

This project is a RESTful web application using the Python framework Flask along with implementing third-party OAuth authentication. Used the various HTTP methods available and utilized them to perform CRUD (create, read, update and delete) operations.
The Item Catalog project consists of developing an application that provides a list of items within a variety of categories, as well as provide a user registration and authentication system.

## Dependencies for Project: ##

1. Flask
2. Vagrant
3. Udacity Vagrantfile
4. VirtualBox

## Instructions on how to run the project: ##

### How to Install: ###

1. Install Vagrant & VirtualBox
2. Clone the fullstack-nanodegree-vm
3. Go to Vagrant directory and either clone this repo or download and place zip here
4. Launch the Vagrant VM (vagrant up)
5. Log into Vagrant VM (vagrant ssh)
6. Navigate to cd/vagrant as instructed in terminal
(If you do not have certain package, run sudo pip install 'Package Name')
7. Setup application database in /Restaurant_ItemCatalog/database_setup.py by using the command python database_setup.py
8. Then set up the required data/tables in the database to be queried by running the command python users.py
9. Run application using the command python project.py
10. Access the application locally by visiting http://localhost:5000



## The following are the JSON endpoints: ##

/restaurants/JSON

/restaurants/<int:restaurant_id>/menu/JSON/

/restaurants/<int:restaurant_id>/menu/<int:menu_id>/JSON/
