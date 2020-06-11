from flask import Flask, render_template, request, session, redirect, url_for, send_file
import os
import uuid
import hashlib
import pymysql.cursors
from functools import wraps
import time

app = Flask(__name__)
app.secret_key = "super secret key"
IMAGES_DIR = os.path.join(os.getcwd(), "images")

connection = pymysql.connect(host="localhost",
                             user="root",
                             password="root",
                             db="finstagram_final",
                             charset="utf8mb4",
                             port=8889,
                             cursorclass=pymysql.cursors.DictCursor,
                             autocommit=True)

## some comments will be for presentation purposes sorry



## helpful function that retuns the query which is a dictionary

#get one or all from the query,
#parameters is the specfic thing you are looking for
def runQuery( query, returnType = None, parameters = None ):
    with connection.cursor( ) as cursor:
        cursor.execute( query, parameters )
    if returnType == "one":
        return cursor.fetchone( )
    if returnType == "all":
        return cursor.fetchall( )
    return

##### All login credentials
def login_required(f):
    @wraps(f)
    def dec(*args, **kwargs):
        if not "username" in session:
            return redirect(url_for("login"))
        return f(*args, **kwargs)
    return dec


#Main page ----------------------------------------------------------------
# main page
@app.route("/")
def index():
    #index html will take user to intial page
    ## this page can change based upon status of being loged in
    #loged in --> user page
    ## not logged in welcome page
    if "username" in session:
        return redirect(url_for("home"))
    return render_template("index.html")

# registration page ----------------------------------------------
#the first thing a user will click is to register
@app.route("/register", methods=["GET"])
def register():
    return render_template("register.html")

# login page-----------------------------------------------------
#The second thing a registered user will do is login

@app.route("/login", methods=["GET"])
def login():
    return render_template("login.html")

# authenticate user -------------------------------
#given to us by a very nice TA
@app.route("/loginAuth", methods=["POST"])
def loginAuth():
    if request.form:
        #request a form from the server
        requestinfo = request.form
        #sets the requested info from server/db to username
        # and password and hashes password
        username = requestinfo["username"]
        plaintextPasword = requestinfo["password"]
        hashedPassword = hashlib.sha256(plaintextPasword.encode("utf-8")).hexdigest()

        with connection.cursor() as cursor:
            ##executes a query to find a corresponding   username
            ## password to Person
            query = "SELECT * FROM Person WHERE username = %s AND password = %s"
            cursor.execute(query, (username, hashedPassword))
        info = cursor.fetchone()
        if info:
            session["username"] = username
            #go home if correct
            return redirect(url_for("home"))

        ## however if not incorrect password
        err = "Incorrect username or password."
        return render_template("login.html", err=err)

    err = "Error has occured.Please try again"
    return render_template("login.html", err=err)


# authenticating new user page--------------------------------------


@app.route("/registerAuth", methods=["POST"])
def registerAuth():
    # info in the from, getting from the form
    if request.form:
        requestinfo = request.form
        username = requestinfo["username"]
        plaintextPasword = requestinfo["password"]
        hashedPassword = hashlib.sha256(plaintextPasword.encode("utf-8")).hexdigest()

        firstName = requestinfo["firstName"]
        lastName = requestinfo["lastName"]

        bio= requestinfo["bio"]

        try:
            with connection.cursor() as cursor:
                query = "INSERT INTO Person (username, password, fname, lname,bio) VALUES (%s, %s, %s, %s,%s)"
                cursor.execute(query, (username, hashedPassword, firstName, lastName,bio))
        except pymysql.err.IntegrityError:
            err = "%s is already taken." % (username)
            return render_template('register.html', err=err)

        return redirect(url_for("login"))

    err = "Error has occured. Please try again"
    return render_template("register.html", err=err)

# home page----------------------------------------------------------------------------
## shown if it is the users home page
@app.route("/home")
@login_required
def home():
    username=session["username"]

    query="SELECT bio FROM Person WHERE username=%s"
    query2=runQuery(query,"one",(username))

    #return render_template("home.html", username=username,bio=query2["bio"])
    return render_template("home.html", username=username,bio=query2["bio"])



# upload photo page. login required
@app.route("/upload", methods=["GET"])
@login_required
def upload():
    return render_template("upload.html")



## Grabbing all the photos info----------------------------------------------
##including if you are tagged

##Grab photo grabs our photo information and is our primary function to help us with everything
def grabPhotoinfo():
    username = session[ "username" ]

    # Select all of the phtos, joing them person
    # We then find where the all the exsiting following and followee EXISTS
    # then order there pictures together
    #Not equal to

    ## very long query but super powerful
    ## allows us to select all the photos, joins them based on the photoOwner and username
    ## then if the username exist in the follow area and the follower and followee followw each other
    ## we see if the are not equal to 0 and if photoall followers are not equal to zero
    ##we then order by time stamp in descending order

    query= "SELECT * FROM Photo JOIN Person ON (Photo.photoOwner = Person.username) WHERE ( (EXISTS (SELECT * FROM Follow WHERE followerUname =%s and followeeUname = Photo.photoOwner AND acceptedFollow <> 0) AND Photo.allFollowers <> 0) OR Photo.photoOwner=%s) ORDER BY Photo.timestamp DESC"
    info = runQuery( query, "all",(username,username))


    #photo information dictionary
    ## use a dictionary because when the project was orginally given ithought
    ##dictionary easy can store everything
    ## we store all the necessary info into pInfo


    pInfo = { }
    for item in info:
        if item["photoID"] not in pInfo:
            pInfo[ item[ "photoID" ] ] = { "currentUser": username,
                                     "filePath": item[ "filePath" ],
                                     "photoOwner": item[ "photoOwner" ],
                                     "name": item[ "fname" ] + " " + item[ "lname" ],
                                     "timestamp": item[ "timestamp" ],
                                     "caption": item[ "caption" ],
                                     "tags": { },
                                     "userIsPhotoOwner": True if username == item["photoOwner" ] else False,
                                     "comments": [ ]
                                    }

    for item[ "photoID" ] in pInfo:

        #grabs all the tags from the {} of the photoID
        #we select all the tags from where the photoId is equal to the one we want
        # we then run the query to get all of them


        query = "SELECT * FROM tag WHERE photoID = %s"
        info = runQuery( query, "all", item[ "photoID" ] )

        #every tag in table where the photoId matches the curent photo
        #check the tag if it has been accepted

        for tag in info:
            tagUser = tag[ "username" ]
            trueTag = tag[ "acceptedTag" ]

            #If tag is accepted add user to tag

            if trueTag:
                pInfo[ item[ "photoID" ] ][ "tags" ][ tagUser ] = True

            #else if set the user tag not accepted to False not accepted
            elif tagUser == username:
                pInfo[ item[ "photoID" ] ][ "tags" ][ tagUser ] = False
    return pInfo




#images page, the login is required-----------------------------------------------------
@app.route("/images", methods=["GET"], defaults = {"err": None } )
@app.route("/images?<err>", methods=["GET"])
@login_required
#err taken in as parameter incase err occurs
def images( err ):

    #grab username from the session photoID,options
    username = session[ "username" ]
    pId = request.args.get( "photoID" )
    op = request.args.get( "option" )
    try:
        # If user accepted tag then true
        if op == "acceptTag":
            query = "UPDATE Tag SET acceptedTag = True WHERE photoID = %s AND username = %s"
            runQuery( query, None, ( pId, username ) )
        #else if its a rejected tag
        #we delete the tag from the table completely nothing happens to the table
        elif op == "rejectTag":
            query = "DELETE FROM Tag WHERE photoID = %s AND username = %s"
            runQuery( query, None, ( pId, username ) )
    #exception the image is given to the URL no tag given
    #duplicate ket
    #This exception is raised when the relational integrity of the data is affected.
    #For example, a duplicate key was inserted or a foreign key constraint would fail.

    ## go to images and render with images
    ## go back to grab all images function

    except pymysql.err.IntegrityError:
        return redirect( url_for( "images" ) )

    # we grab all photo info and give it to the template
    ## go back to grab photo info to grab all the information for this photo
    pInfo = grabPhotoinfo( )
    return render_template("images.html", err = err, images = pInfo )



# image page for only one image --------------------------------------------------
@app.route("/image/<image_name>", methods=["GET"])
def image(image_name):
    image_location = os.path.join(IMAGES_DIR, image_name)
    if os.path.isfile(image_location):
        return send_file(image_location, mimetype="image/jpg")




## uploading an image ---------------------------------------------------------------
@app.route("/uploadImage", methods=["POST"])
@login_required
def upload_image():
    try:


        #we grab the image name, filepath , username and caption
        image_file = request.files.get("imageToUpload", "")
        image_name = image_file.filename
        ##grabs image directory from os path
        filepath = os.path.join(IMAGES_DIR, image_name)
        image_file.save(filepath)
        username = session[ "username" ]
        caption = request.form[ "caption" ]

        # if user checks allFollowers, set to true, else set false

        ##check if all followers can view
        try:
            #request form for all followers to see if it true
            if request.form[ "allFollowers" ]:
                allFollowers = True
        except:
            allFollowers = False

        # insert photo
        query = "INSERT INTO\
                Photo( photoOwner, timestamp, filePath, caption, allFollowers)\
                VALUES ( %s, %s, %s, %s, %s )"

        #make sure to insert time stamp
        #query grab photoID of photo and insert to last upload
        # in this case when we call the run query we place a NONE type for the one ,all as we dont want
        #any
        #parameters will be the username which we defined above and time

        runQuery( query, None, (username, time.strftime('%Y-%m-%d %H:%M:%S'),image_name, caption, allFollowers ) )

        #select last_inset_ID grabs last elem
        #grab last element of the last photo we inserted because you know
        #last photo we recently uploaded its important

        query = "SELECT LAST_INSERT_ID()"

        #grabs single last elem
        info = runQuery( query, "one", None )
        #last photo ID

        pId = info[ "LAST_INSERT_ID()" ]

        # if we are  sharing our photos with not our followers

        print(allFollowers,"first")
        if not allFollowers:

            print(allFollowers)


            #grab the groups of the current not out user
            query = "SELECT groupName, groupOwner\
                    FROM Belong\
                    WHERE username = %s"
            info = runQuery( query, "all", username )
            groupAndOwner = [ ]
            #make a list of the owners group

            #append every group oweners groupName
            for elem in info:
                groupAndOwner.append( [ elem[ "groupName" ], elem[ "groupOwner" ] ] )


            #insert the group owner and the group names, and the photo ids into a collobrative
            #share table means that we will be able to see all the images
            for groupOwner in groupAndOwner:

                query = "INSERT INTO Share VALUES ( %s, %s, %s )"
                runQuery( query, None, ( groupOwner[ 0 ], groupOwner[ 1 ], pId ) )
            text = "Image has been succesfully privately"
            #image was scuessfuly upladed and we are not sharing with our followers
        else:
            text = "Image was uploaded to our followers "
        return render_template("upload.html", text=text)
    #
    except:
        text = "Failed image upload"
        return render_template("upload.html", text=text)


#viewing the followers page  -----------------------------------------------------------
@app.route( "/follow", methods = ["GET"], defaults = {"err": None} )
@app.route( "/follow?<err>", methods = ["GET"] )
@login_required
def follow( err ):

    #grabing username and options
    currUser = session[ "username" ]
    op = request.args.get( "option" )
    followUname = request.args.get( "username" )

    #if the user has accepted the request
    if op == "accept":
        query = "UPDATE Follow SET acceptedfollow = True WHERE followerUname = %s AND followeeUname = %s"
        runQuery( query, None, ( followUname, currUser ) )
    #we got declined and delete request
    if op == "reject":
        query = "DELETE FROM Follow WHERE followerUname = %s AND followeeUname = %s"
        runQuery( query, None, ( followUname, currUser ) )

    #grab all follow request
    #followee=ourselves , we havent accepted request
    query = "SELECT followerUname FROM Follow WHERE followeeUname = %s AND acceptedfollow = False"
    #grabbing all the follow request
    info = runQuery( query, "all", currUser )
    #request list

    ## MAke a list of all the request these reuqest are then used to place
    ## all of the follwer name
    requests = [ ]
    for elem in info:
        #append all those who want to follow us
        requests.append( elem[ "followerUname" ] )

    #grab all we followrs but we are the followee
    query = "SELECT followeeUname FROM Follow WHERE followerUname = %s AND acceptedfollow = True"
    info = runQuery( query, "all", currUser )

    ## list of all followers
    followers = [ ]
    for elem in info:
        #print("im here baffon")
        followers.append( elem[ "followeeUname" ] )


    #grab all the followees, if we are the follower
    query = "SELECT followerUname FROM Follow WHERE followeeUname = %s AND acceptedfollow = True"
    info = runQuery( query, "all", currUser )

    ## list of all the followees
    followees = [ ]
    for elem in info:
        #print("here")
        followees.append( elem[ "followerUname" ] )

    ## Then render the template with all of them

        #followers matches the following , request matches the follow request ,followees matches the followed by
    return render_template( "follow.html", err = err,requests = requests, followers = followers, followees = followees )


## authenticate follower, grab follower username
@app.route( "/followAuth", methods = ["POST"] )
@login_required
def followAuth( ):
    if request.form:
        #grab the followee and follower
        followerUname = session[ "username" ]
        followeeUname = request.form[ "followeeUname" ]

        #cant follow yourself
        if followerUname == followeeUname:
            return redirect( url_for( "follow", err = "You cannot follow yourself" ) )

        # see if person is in table
        query = "SELECT * FROM Person WHERE username = %s"
        #grab the single person
        info = runQuery( query, "one", followeeUname )
        if not info:
            #person does not exist
            err = "%s does not exist" %( followeeUname )
            return redirect( url_for( "follow", err = err ) )

        #add into follows
        try:
            query = "INSERT INTO Follow VALUES( %s, %s, %s )"
            #take none since we are adding
            runQuery( query, None, ( followerUname, followeeUname, False ) )
            #success request has been sent
            err = "Request to %s has been sent" %( followeeUname )
        except pymysql.err.IntegrityError:
            err = "Request sent or you already already follow %s" %( followeeUname )
        return redirect( url_for( "follow", err = err ) )
    else:
        #both things failed so um its all my fault (programmer )
        err = "Error occured please try again"
        return redirect( url_for( "follow", err = err ) )


# post method to tag person into a photo
@app.route( "/tagUser", methods = [ "POST" ] )
@login_required
def tagUser( ):
    if request.form:
        #grab tag users name
        tagUser = request.form[ "taggedUser" ]
        if len( tagUser ) == 0:
            return redirect( url_for( "images", err = "you must enter a name" ) )


        #grab photo id of owner
        pId = request.args.get( "photoID" )
        query = "SELECT photoOwner FROM photo WHERE photoID = %s"
        photoOwner = runQuery( query, "one", pId )[ "photoOwner" ]



        #Check to see if request has been sent or accepted
        query = "SELECT * FROM tag WHERE photoID = %s AND username = %s"
        info = runQuery( query, "one", ( pId, tagUser ) )
        if info:
            print(info)

            if info["acceptedTag"]:
                #print("Im here")
                #person is tagged already
                err = " %s already tagged" %( tagUser )
                #print("Im here")
                return redirect( url_for( "images", err = err ) )

            #tag request has been sent already

            err = "tag request to  %s has been sent" %( tagUser )
            return redirect( url_for( "images", err = err ) )

        # #if we are tagged the user then we add to the table
        #
        # queryIN="SELECT * FROM tag WHERE photoID = %s AND username = %s AND acceptedTag=True"
        # info2=runQuery(queryIN,"all",(pId,tagUser))
        #
        # if info2:
        #     print("Hey we are tagged already")
        #     err = " %s already tagged" %( tagUser )
        #     return redirect( url_for( "images", err = err ) )




        if tagUser == session[ "username" ]:
            #print("I tagged myself")
            query = "INSERT INTO Tag VALUES( %s, %s, True )"
            runQuery( query, None, ( tagUser, pId ) )
            err = "successfully tagged %s" %( tagUser )
            return redirect( url_for( "images", err = err ) )


        ## handles shared or not shared
        ##also if photo is private or not private to the user
        #if photoOwner is not the tagged user
        # you cant follow yourself
        if photoOwner != tagUser:
            # grab the photos to share with followers
            query = "SELECT allFollowers FROM photo WHERE photoID = %s"
            allFollowers = runQuery( query, "one", pId )
            #if we are sharing with everyone , check if tagged is follower of curr user


            if allFollowers["allFollowers"]:
                ## handles if is private
                ###query if we are following each other and therefore we can grab the single follower and tag them

                query = "SELECT * FROM follow WHERE followerUname = %s AND followeeUname = %s AND acceptedFollow = 1"

                info = runQuery( query, "one", ( tagUser, photoOwner ) )

                #err cant tag because you dont follow
                if not info:
                    err = "Cant tag %s you do not follow  %s" %( tagUser, photoOwner )
                    #now based on that we can render the html to fit that we cannot tag them
                    return redirect( url_for( "images", err = err ) )


            #else check if the tagged user is in the same Friendgroup as the current user

            #we select all from belong
            #where b1 and b2 and yse both group NAme and Group Owner to check the usernames to see if they match
            ## if match we grab the single tagUser and photoOwner which are from the current session and from the ran query

            


            else:
                query = "SELECT * FROM Belong AS b1 JOIN Belong AS b2 USING( groupName, groupOwner ) WHERE b1.username = %s AND b2.username = %s"

                info = runQuery( query, "one", ( tagUser, photoOwner ) )

                ##tagged User isnt a follower return an err
                if not info:
                    err = "you cannot tag %s as this cant be shared with followers\
                            as %s" %( tagUser, photoOwner )
                        #render html to show that the person is not part of your followers yet and the picture is private
                    return redirect( url_for( "images", err = err ) )

        # inserting the tag into the tag table. if there is an err,
        # that means there already is a tagged request for the user

        #Insert tag into tag table
        query = "INSERT INTO Tag VALUES( %s, %s, False )"
        runQuery( query, None, ( tagUser, pId ) )
        err = "Request has been sent to %s" %( tagUser )
        return redirect( url_for( "images", err = err ) )
    # if form wasnt submitted
    err = "something went wrong, Try again! "
    return redirect( url_for( "images", err = err ) )


# logout page
@app.route("/logout", methods=["GET"])
def logout():
    session.pop("username")
    return redirect("/")

if __name__ == "__main__":
    if not os.path.isdir("images"):
        os.mkdir(IMAGES_DIR)
    app.run(debug = True)
