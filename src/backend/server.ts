import express from "express";
import cors from "cors";
import bcrypt from "bcryptjs";
import prisma from "./prisma";

const app = express();

app.use(cors());
app.use(express.json());

app.get("/", (req, res) => {
  res.send("Backend Running");
});

app.post("/register", async (req, res) => {
  try {
    const { fullName, email, password } = req.body;

    // Check existing user
    const existingUser = await prisma.user.findUnique({
      where: {
        email,
      },
    });

    if (existingUser) {
      return res.json({
        message: "User already exists",
      });
    }

    // Hash password
    const hashedPassword = await bcrypt.hash(
      password,
      10
    );

    // Save user
    const user = await prisma.user.create({
      data: {
        fullName,
        email,
        password: hashedPassword,
      },
    });

    res.json({
      success: true,
      message: "User registered successfully",
      user,
    });
  } catch (error) {
    console.log(error);

    res.status(500).json({
      message: "Server Error",
    });
  }
});

app.listen(5000, () => {
  console.log("Server running on port 5000");
});