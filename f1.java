import java.util.Arrays;

public class f1 {
    public static void main(String[] args) {
        int[][] arr = {
            {55, 2, 12},
            {77, 8, 88},
            {2, 3, 1}
        };

        System.out.println("Original Array:");
        print2DArray(arr);

        // 1. Inner Sorting (sort each row)
        for (int i = 0; i < arr.length; i++) {
            Arrays.sort(arr[i]);
        }

        System.out.println("\nAfter Inner Sorting (each row sorted):");
        print2DArray(arr);

        // 2. External Sorting (flatten + sort)
        int total = 0;
        for (int[] row : arr) {
            total += row.length;
        }

        int[] flat = new int[total];
        int index = 0;
        for (int[] row : arr) {
            for (int val : row) {
                flat[index++] = val;
            }
        }

        // Keep track of original indexes before sorting
        int[][] indexed = new int[flat.length][2]; 
        for (int i = 0; i < flat.length; i++) {
            indexed[i][0] = flat[i]; // value
            indexed[i][1] = i;       // original index
        }

        // Sort by values
        Arrays.sort(indexed, (a, b) -> Integer.compare(a[0], b[0]));

        System.out.println("\nAfter External Sorting (entire array sorted):");
        for (int[] pair : indexed) {
            System.out.print(pair[0] + " ");
        }

        System.out.println("\n\nOriginal Indexes of Sorted Elements:");
        for (int[] pair : indexed) {
            System.out.print(pair[1] + " ");
        }
    }

    // Helper to print 2D array
    public static void print2DArray(int[][] arr) {
        for (int[] row : arr) {
            for (int val : row) {
                System.out.print(val + " ");
            }
            System.out.println();
        }
    }
}
