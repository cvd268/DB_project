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


## First I will handle all the necessary quiries

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

## Grabbing all the photos info----------------------------------------------
##including if you are tagged
def grabPhotoinfo():
    username = session[ "username" ]

    # Select all of the phtos, joing them person
    # We then find where the all the exsiting following and followee EXISTS
    # then order there pictures together

    query= "SELECT * FROM Photo JOIN Person ON (Photo.photoOwner = Person.username) WHERE ( EXISTS (SELECT * FROM Follow WHERE followerUname =%s and followeeUname = Photo.photoOwner) OR Photo.photoOwner=%s) ORDER BY Photo.timestamp DESC"
    info = runQuery( query, "all",(username,username))
    #photo information dictionary
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
        query = "SELECT *FROM tag WHERE photoID = %s"
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

## comment later
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
        except pymysql.err.Integrityerr:
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
    return render_template("home.html", username=username,bio=query2)



# upload photo page. login required
@app.route("/upload", methods=["GET"])
@login_required
def upload():
    return render_template("upload.html")

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
        elif op == "rejectTag":
            query = "DELETE FROM Tag WHERE photoID = %s AND username = %s"
            runQuery( query, None, ( pId, username ) )
    #exception the image is given to the URL no tag given
    except pymysql.err.Integrityerr:
        return redirect( url_for( "images" ) )

    # we grab all photo info and give it to the template
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
        filepath = os.path.join(IMAGES_DIR, image_name)
        image_file.save(filepath)
        username = session[ "username" ]
        caption = request.form[ "caption" ]

        # if user checks allFollowers, set to true, else set false

        ##check if all followers can view
        try:

            if request.form[ "allFollowers" ]:
                allFollowers = True
        except:
            allFollowers = False

        # inser photo
        query = "INSERT INTO\
                Photo( photoOwner, timestamp, filePath, caption, allFollowers)\
                VALUES ( %s, %s, %s, %s, %s )"

        #make sure to insert time stamp
        #query grab photoID of photo and insert to last upload
        runQuery( query, None, (username, time.strftime('%Y-%m-%d %H:%M:%S'),image_name, caption, allFollowers ) )

        #select last_inset_ID grabs last elem
        query = "SELECT LAST_INSERT_ID()"

        #grabs single last elem
        info = runQuery( query, "one", None )
        #last photo ID

        pId = info[ "LAST_INSERT_ID()" ]



        # if we're sharing the photo with our friends group,
        if not allFollowers:


            #grab the groups of the current user
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
            text = "Image has been succesfully loaded to Friendgroup"
        #image was scuessfuly upladed
        else:
            text = "Image was uploaded"
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
    currentUsername = session[ "username" ]
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
    requests = [ ]
    for elem in info:
        #append all those who want to follow us
        requests.append( elem[ "followerUname" ] )

    #grab all we follow
    query = "SELECT followeeUname FROM Follow WHERE followerUname = %s AND acceptedfollow = True"

    info = runQuery( query, "all", currUser )
    followers = [ ]
    for elem in info:
        followers.append( elem[ "followeeUname" ] )

    #grab all the followees, if we are the followee
    query = "SELECT followerUname FROM Follow WHERE followeeUname = %s AND acceptedfollow = True"
    info = runQuery( query, "all", currUser )
    followees = [ ]
    for elem in info:
        followees.append( elem[ "followerUname" ] )
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
            err = "%s does not exist" %( followeeUname )
            return redirect( url_for( "follow", err = err ) )

        #add into follows
        try:
            query = "INSERT INTO Follow VALUES( %s, %s, %s )"
            runQuery( query, None, ( followerUname, followeeUname, False ) )
            #success request has been sent
            err = "Request to %s has been sent" %( followeeUname )
        except pymysql.err.Integrityerr:
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
            err = "tag request to  %s has been sent or already tagged" %( tagUser )
            return redirect( url_for( "images", err = err ) )

        #if we are tagged the user then we add to the table

        if tagUser == session[ "username" ]:
            query = "INSERT INTO Tag VALUES( %s, %s, True )"
            runQuery( query, None, ( tagUser, pId ) )
            err = "successfully tagged %s" %( tagUser )
            return redirect( url_for( "images", err = err ) )



        #if photoOwner is not the tagged user
        # you cant follow yourself
        if photoOwner != tagUser:
            # grab the photos to share with followers
            query = "SELECT allFollowers FROM photo WHERE photoID = %s"
            allFollowers = runQuery( query, "one", pId )
            #if we are sharing with everyone , check if tagged is follower of curr user

            if allFollowers["allFollowers"]:
                query = "SELECT * FROM follow WHERE followerUname = %s AND followeeUname = %s AND acceptedFollow = 1"

                info = runQuery( query, "one", ( tagUser, photoOwner ) )

                #err cant tag because you dont follow
                if not info:
                    err = "Cant tag %s you do not follow  %s" \
                            %( tagUser, photoOwner )
                    return redirect( url_for( "images", err = err ) )


            #else check if the tagged user is in the same Friendgroup as the current user
            else:
                query = "SELECT * FROM belong AS b1 JOIN belong AS b2 USING( groupName, groupOwner ) WHERE b1.username = %s AND b2.username = %s"
                info = runQuery( query, "one", ( tagUser, photoOwner ) )

                ##tagged User isnt a follower return an err
                if not info:
                    err = "you cannot tag %s as they are not in the Friendgroup\
                            as %s" %( tagUser, photoOwner )
                    return redirect( url_for( "images", err = err ) )

        # try inserting the tag into the tag table. if there is an err,
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
