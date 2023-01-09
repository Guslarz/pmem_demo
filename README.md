# pmem_demo

This project is a brief explanation on what Persistent memory is and how to use it in Python. It can be used as a starting point for python development for pmem.

# Overview 
In a normal Python program we create a bunch of objects and use them to accomplish a goal. When the program ends, all of the objects are thrown away, to be rebuilt from scratch the next time the program is run. pmemobj provides the opportunity to change this paradigm: to be able to create objects in a program, and have their state preserved between program runs, so that they do not need to be reconstructed the next time the program is run. The guarantee made by pmemobj is that the state of the objects will be self-consistent no matter when the program terminates. Further, it provides a transaction() that can be placed around multiple persistent object modifications to guarantee that either all of the modifications are made, or none of them are made.

Contrast this with a persistence paradigm such as that provided by SQL Alchemy. Here we have objects whose data is mapped to relational database tables. When the program starts up, it can query the database in any of several ways in order to retrieve objects. The object state is thus persistent in the sense that an object will have the same state it had the last time that object was flushed to disk in a previous program. SQLAlchemy also provides transactions that guarantee that either all of the changes in a block are committed to the database, or none of them are.

So, how do the two paradigms differ? At the higher conceptual levels, not by much. In the SQLAlchemy case objects are retrieved by running a query to find selected instances of a given object class. In pmemobj objects are retrieved by walking an object tree from a root object defined by the program. The difference, for both better and worse, is that persistent memory is entirely an “object store”, and not a relational database. It is thus more similar to the ZODB than to SQLAlchemy.

Where it differs from the ZODB is in how objects are stored. In the ZODB Python objects are serialized using the pickle module and stored on disk. In pmemobj, objects are stored directly in persistent memory, written to and read from using the same store and fetch instructions used to access RAM memory. This means that in principle read access can be nearly as fast as RAM access, and write access can be orders of magnitude more efficient than disk writes.

In practice we’re at the early stages of development, and at least in the Python case we aren’t anywhere near as fast as we could be. But it’s fast enough to be useful.

To be a bit more concrete, consider the example of a Python list. CPython stores a list in RAM via an object header that points to an area of allocated memory that holds a list of pointers to the objects in the list. In pmemobj, a list is stored in persistent memory as an object header that points to an area of allocated persistent memory that contains a list of persistent pointers to the objects in the list. An access to a list element is a normal addr+offset fetch of a pointer. Pointer resolution is another quick arithmetic operation. Updating a list element is the reverse: calculating the persistent pointer to the object and storing it at the correct offset in the persistent data structure. It is clear that this is going to be more efficient than SQLAlchemy marshalling to SQL-DB-update to disk-write to disk-flush, or ZODB-pickling to disk-write to disk-flush.

There is, however, overhead involved in the integrity guarantees. libpmemobj uses a change-log to record all changes that are taking place in a transaction, and if the transaction is aborted or not marked as complete, then all of the changes that did take place during the aborted transaction are rolled back, either immediately in the case of an abort, or the next time the persistent memory is accessed by libmemobj in the case of a crash. This log overhead has a non-zero cost, but what you buy with that cost is the object and transactional integrity in the face of hard crashes. And all of the log and rollback activity takes place using direct memory fetch and store instructions, so it is still fast, relatively speaking.

In this first version of pmemobj we have focused on proof of concept and portability rather than efficiency. That is, it is implemented entirely in Python, using CFFI to access the libpmemobj functions. In addition, most immutable persistent objects are handled by converting them back to normal Python RAM based instances when accessed, rather than accessing them directly in persistent memory. All of this adds conceptually unnecessary overhead and results in execution times that are slower than optimal. There is no conceptual barrier, however, to making it all quite efficient by moving the object access to the C level in a future version. The object algorithms are, for the most part, copied directly from the CPython codebase, with a few modifications to deal with persistent pointers and updating the rollback log. So in principle the object implementations can be almost as fast as the CPython objects they are emulating.

# Emulating Persistent Memory 

“Real” persistent memory in the context of this library is physical non-volatile memory that is accessible via the linux kernel DAX extensions. Persistent memory thus configured appears as a mounted filesystem to Linux. An allocated area of persistent memory is labeled by a filename according to normal unix rules. Thus if your DAX memory is mounted at /mnt/persistent, your would refer to an allocated area of memory named `myprog.pmem` via the path:

```/mnt/persistent/myprog.pmem```

The persistent file system is a normal unix filesystem when viewed through the file system drivers. The magic of DAX, however, is that it allows a program to bypass the file system drivers and have direct, unbuffered access to the memory using normal CPU fetch and store instructions. There are, of course, concerns with respect to CPU caches and when exactly a change gets committed to the physical memory. See the pmem module for more details. pmemobj handles all of those details so your program doesn’t have to.

There are two sorts of “fake” persistent memory. One is discussed on the Persistent Memory Wiki referenced above: you can emulate real persistent memory using regular RAM by reserving RAM to accessed through DAX via kernel configuration.

The second sort of “fake” persistent memory is to simply `mmap` a normal file. In this case the pmem libraries use different calls to ensure changes are flushed to disk, but the remainder of the pmem programming infrastructure can be tested. All of the pmem libraries automatically use this mode when the specified path is not a DAX-backed path.

So, anywhere in the following examples where a filename is used, you can substitute a path that will access the fake or real persistent memory as you choose, and the examples should all work the same. (Except for losing the persistent data on machine reboot, if you are using RAM emulation.)

# Object types

For the purposes of considering persistence, we can divide Python objects up into three classes: immutable non-container objects, mutable non-container objects, and container objects.

Immutable non-container objects are the easiest to handle. We can store them in whatever form we want in persistent memory, and upon access we can reconstruct the equivalent Python object and let the program use that. Because the object is immutable, it doesn’t matter that the object in persistent memory and object in use aren’t the same object. (Or if it does, that’s a bug in your program, since Python makes no guarantees about the identity of immutable objects.)

Mutable non-container objects must directly store, update, and retrieve their data from persistent memory, since everything that points to that mutable object will expect to see any updates. (An example of a mutable non-container object is a bytearray. pmemobj does not yet support any of Python’s mutable non-container types.)

Container objects may contain pointers to other objects. The rule in pmemobj is that every object pointed to by a persistent container must itself be stored persistently. This means that all pointers inside persistent objects are persistent pointers; that is, pointers that can be resolved into a valid pointer if the program is shut down and restarted running in a different memory location. Therefore we can’t map a persistent immutable container object (such as a tuple) to its Python equivalent, because the stored pointers are persistent pointers, and may not even have the same length as a normal RAM pointer.

Mostly these distinctions matter only to someone implementing a new persistent type. However, the first category, the immutable non-container objects, matter at the Python programming level. This is because there are two possibilities for such objects: pmemobj may support them directly, or it may support them through pickle. If a class is supported directly, a Pesistent container may reference them and pmemobj will automatically deal with storing their data persistently, and accessing it when referenced. If a class is not supported directly, then a program using pmemobj can still reference them, if the program nominates them for persistence via pickling. This is less efficient than direct support, but allows programs to use data types for which support has not yet been written. (Pickling is not applied automatically because there is no way for pmemobj to determine if a specific class is immutable or not.)

# Guessing game

Repository caontains exaple source code fo number guessing game that is utilizing persistent memory to store game state.
