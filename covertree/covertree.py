# File: covertree.py
# Date of creation: 05/04/07
# Copyright (c) 2007, Thomas Kollar <tkollar@csail.mit.edu>
# Copyright (c) 2011, Nil Geisweiller <ngeiswei@gmail.com>
# All rights reserved.
#
# This is a class for the cover tree nearest neighbor algorithm.  For
# more information please refer to the technical report entitled "Fast
# Nearest Neighbors" by Thomas Kollar or to "Cover Trees for Nearest
# Neighbor" by John Langford, Sham Kakade and Alina Beygelzimer
#  
# If you use this code in your research, kindly refer to the technical
# report.

from copy import deepcopy
from random import choice
from heapq import nsmallest 
import sys

# the Node representation of the data
class Node:
    # data is an array of values
    def __init__(self, data=None):
        self.data = data
        self.children = {}      # dict mapping level and children
        self.parent = None

    # addChild adds a child to a particular Node and a given level
    def addChild(self, child, level):
        try:
            # in case level is not in self.children yet
            if(child not in self.children[level]):
                self.children[level].append(child)
        except(KeyError):
            self.children[level] = [child]
        child.parent = self

    # getChildren gets the children of a Node at a particular level
    def getChildren(self, level):
        retLst = [self]
        try:
            retLst.extend(self.children[level])
        except(KeyError):
            pass
        
        return retLst

    # like getChildren but does not return the parent
    def getOnlyChildren(self, level):
        try:
            return self.children[level]
        except(KeyError):
            pass
        
        return []


    def removeConnections(self, level):
        if(self.parent != None):
            #print self.parent.children
            self.parent.children[level+1].remove(self)
            self.parent = None

    def __str__(self):
        return str(self.data)
    
    def __repr__(self):
        return str(self.data)

class CoverTree:
    
    #
    # Overview: initalization method
    #
    # Input: distance function, root, maxlevel, minlevel Here root is
    #  a point, maxlevel is the largest number that we care about
    #  (e.g. base^(maxlevel) should be our maximum number), just as
    #  base^(minlevel) should be the minimum distance between Nodes.
    # Output:
    #
    def __init__(self, distance, root = None, maxlevel = 10, base = 2):
        self.distance = distance
        self.root = root
        self.maxlevel = maxlevel
        self.minlevel = maxlevel # the minlevel will adjust automatically
        self.base = base
        # for printDotty
        self.printHash = {}


    #
    # Overview: insert an element p into the tree
    #
    # Input: p
    # Output: nothing
    #
    def insert(self, p):
        if self.root == None:
            self.root = Node(p)
        else:
            self.insert_iter(p)

            
    #
    # Overview: behaves like knn(p, k) and insert(p). This method exists for efficiency reason
    #
    # Input: point p, and k the number of nearest neighbors to return
    #
    # Output: Nearest points with respect to the distance metric
    #          self.distance()
    #
    def knn_insert(self, p, k):
        return self.knn_insert_iter(p, k)
        
    #
    # Overview: get the k-nearest neighbors of an element
    #
    # Input: point p, and k the number of nearest neighbors to return
    #
    # Output: Nearest points with respect to the distance metric
    #          self.distance()
    #
    def knn(self, p, k):
        return self.knn_iter(p, k)

    #
    # Overview: find an element in the tree
    #
    # Input: Node p
    # Output: True if p is found False otherwise and the level of p
    #
    def find(self, p):
        return self.find_rec(p, [self.root],
                             [self.distance(p, self.root.data)],
                             self.maxlevel)


    #
    # Overview:insert an element p in to the cover tree
    #
    # Input: point p
    #
    # Output: nothing
    #
    def insert_iter(self, p):
        Qi = [self.root]
        Qi_p_ds = [self.distance(p, self.root.data)]
        i = self.maxlevel
        while True:
            # get the children of the current level
            # and the distance of the all children
            Q, Q_p_ds = self.getChildrenDist(p, Qi, Qi_p_ds, i)
            d_p_Q = min(Q_p_ds)

            if d_p_Q == 0.0:    # already there no need to insert
                return
            elif d_p_Q > self.base**i: # we found the parent level
                pi = i + 1
                # choose the parent and insert p
                possParents = [q for q, d in zip(Qi, Qi_p_ds)
                               if d <= self.base**pi]
                choice(possParents).addChild(Node(p), pi)
                # update self.minlevel
                self.minlevel = min(self.minlevel, pi)
                return
            else: # d_p_Q <= self.base**i, keep iterating
                # construct Q_i-1
                zn = [(q, d) for q, d in zip(Q, Q_p_ds) if d <= self.base**i]
                Qi = [q for q, _ in zn]
                Qi_p_ds = [d for _, d in zn]
                i -= 1


    #
    # Overview:get the nearest neighbor, iterative
    #
    # Input: query point p
    #
    # Output: the nearest Node 
    #
    def knn_iter(self, p, k):
        Qi = [self.root]
        Qi_p_ds = [self.distance(p, self.root.data)]
        for i in reversed(xrange(self.minlevel, self.maxlevel + 1)):
            #get the children of the current Q and
            #the best distance at the same time
            Q, Q_p_ds = self.getChildrenDist(p, Qi, Qi_p_ds, i)
            d_p_Q = nsmallest(k, Q_p_ds)[-1]

            #create the next set
            zn = [(q, d) for q, d in zip(Q, Q_p_ds)
                  if d <= d_p_Q + self.base**i]
            Qi = [q for q, _ in zn]
            Qi_p_ds = [d for _, d in zn]

        #find the minimum
        return self.args_min(Qi, Qi_p_ds, k)


    #
    # Overview: query the k-nearest points from p and then insert p in
    # to the cover tree (at no additional cost)
    #
    # Input: point p
    #
    # Output: nothing
    #
    def knn_insert_iter(self, p, k):
        Qi = [self.root]
        Qi_p_ds = [self.distance(p, self.root.data)]
        i = self.maxlevel
        found_parent = False
        while not found_parent or i >= self.minlevel:
            # get the children of the current level
            # and the distance of all children
            Q, Q_p_ds = self.getChildrenDist(p, Qi, Qi_p_ds, i)
            d_k = nsmallest(k, Q_p_ds)
            d_p_Q_h = d_k[-1]
            d_p_Q_l = d_k[0]
        
            if not found_parent and d_p_Q_l > self.base**i:
                pi = i + 1
                parent = choice([q for q, d in zip(Qi, Qi_p_ds)
                                 if d <= self.base**pi])
                found_parent = True

            # construct Q_i-1
            zn = [(q, d) for q, d in zip(Q, Q_p_ds)
                  if d <= d_p_Q_h + self.base**i]
            Qi = [q for q, _ in zn]
            Qi_p_ds = [d for _, d in zn]
            i -= 1

        self.minlevel = min(self.minlevel, pi) # update self.minlevel
        parent.addChild(Node(p), pi)

        # find the minimum
        return self.args_min(Qi, Qi_p_ds, k)


    #
    # Overview: find an element given a particular level, recursive
    #
    # Input: point p to find, cover set Qi, current level i
    #
    # Output: True if p is found False otherwise and the level of p
    #
    def find_rec(self, p, Qi, Qi_p_ds, i):
        #get the children of the current level
        Q, Q_p_ds = self.getChildrenDist(p, Qi, Qi_p_ds, i)
        zn = [(q, d) for q, d in zip(Q, Q_p_ds) if d <= self.base**i]
        Qi_next = [q for q, _ in zn]
        Qi_next_p_ds = [d for _, d in zn]
        d_p_Qi = min(Qi_p_ds)

        if(i < self.minlevel):
            return False, None
        elif(d_p_Qi == 0):
            return True, i
        else:
            return self.find_rec(p, Qi_next, Qi_next_p_ds, i-1)


    #
    # Overview: get the children of cover set Qi at level i and the
    # distances of them with point p
    #
    # Input: point p to compare the distance with Qi's children, and
    # Qi_p_ds the distances of all points in Qi with p
    #
    # Output: the children of Qi and the distances of them with point
    # p
    #
    def getChildrenDist(self, p, Qi, Qi_p_ds, i):
        Q = sum([n.getOnlyChildren(i) for n in Qi], [])
        Q_p_ds = [self.distance(p, q.data) for q in Q]
        return Qi + Q, Qi_p_ds + Q_p_ds



    #
    # Overview:get the argument that has the minimum distance
    #
    # Input: Input cover set Q, distances of all nodes of Q to some point
    # Output: minimum distance points in Q to that point
    #
    def args_min(self, Q, Q_p_ds, k):
        z = nsmallest(k, zip(Q, Q_p_ds), lambda x: x[1])
        return [q.data for q, _ in z]

    #
    #Overview:print to the terminal the dot representation
    #  of the stuff
    #
    #Input: None
    #Output: Dotty representation of the cover tree printed to the screen
    #
    def printDotty(self):
        print "digraph {"
        self.printHash = {}
        self.printTree([self.root], self.maxlevel)

        for i in self.printHash.keys():
            print i
        print "}"


    #
    #Overview:recursively print the tree (helper function for printDotty)
    #
    #Input: T ???
    #Output: Dotty representation of the cover tree printed to the screen
    #
    def printTree(self, T, level):
        if(level < self.minlevel):
            return

        thechildren = []
        for p in T:
            childs = deepcopy(p.getChildren(level))

            for i in p.getChildren(level):
                # This piece of code is not used
                # if(level < 0):
                #     mylev = "_" + str(abs(level))
                # else:
                #     mylev = str(level)

                self.printHash["\"lev:" +str(level) + " " + str(p.data) + "\"->\"lev:" + str(level-1) + " " + str(i.data) + "\""] = 0

            thechildren.extend(childs)
        
        self.printTree(thechildren, level-1)

