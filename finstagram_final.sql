CREATE Schema finstagram_q;

Use finstagram_q;


CREATE TABLE Person(
    username VARCHAR(20),
    password CHAR(64),
    fname VARCHAR(20),
    lname VARCHAR(20),
    bio VARCHAR(1024),
    PRIMARY KEY (username)
);

CREATE TABLE Photo(
    photoID int NOT NULL AUTO_INCREMENT,
    photoOwner VARCHAR(20),
    timestamp Timestamp,
    filePath VARCHAR(2048),
    caption VARCHAR(1024),
    allFollowers Boolean,
    PRIMARY KEY (photoID),
    FOREIGN KEY (photoOwner) REFERENCES Person(username)
);

CREATE TABLE Follow(
    followerUname VARCHAR(20),
    followeeUname VARCHAR(20),
    acceptedfollow Boolean,
    PRIMARY KEY (followerUname, followeeUname),
    FOREIGN KEY (followerUname) REFERENCES Person(username),
    FOREIGN KEY (followeeUname) REFERENCES Person(username)
);

---Groups in this context are people you share with it was just easier
-- for me to think of it this way 

CREATE TABLE FriendGroup(
    groupName VARCHAR(20),
    groupOwner VARCHAR(20),
    PRIMARY KEY (groupName, groupOwner),
    FOREIGN KEY (groupOwner) REFERENCES Person(username)
);

CREATE TABLE Belong(
    groupName VARCHAR(20),
    groupOwner VARCHAR(20),
    username VARCHAR(20),
    PRIMARY KEY (groupName, groupOwner, username),
    FOREIGN KEY (groupName, groupOwner) REFERENCES FriendGroup(groupName, groupOwner),
    FOREIGN KEY (username) REFERENCES Person(username)
);

CREATE TABLE Share(
    groupName VARCHAR(20),
    groupOwner VARCHAR(20),
    photoID int,
    PRIMARY KEY (groupName, groupOwner, photoID),
    FOREIGN KEY (groupName, groupOwner) REFERENCES FriendGroup(groupName, groupOwner),
    FOREIGN KEY (photoID) REFERENCES Photo(photoID)
);


CREATE TABLE Tag(
    username VARCHAR(20),
    photoID int,
    acceptedTag Boolean,
    PRIMARY KEY (username, photoID),
    FOREIGN KEY (username) REFERENCES Person(username),
    FOREIGN KEY (photoID) REFERENCES Photo(photoID)
);
