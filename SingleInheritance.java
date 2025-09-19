class Parent {
   public static int 
       count = 0;

    public static void fun1() {
        count--;
        System.out.println("Parent count after decrement: " + count);
    }
}

class Child extends Parent {
    public static void fun2() {
        count++; 
        System.out.println("Child count after increment: " + count);
    }
}

public class SingleInheritance {
    public static void main(String[] args) {
        Child obj = new Child();

        obj.fun2(); 
        obj.fun2(); 

        obj.fun1(); 
        obj.fun1(); 
    }
}
